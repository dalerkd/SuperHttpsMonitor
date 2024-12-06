import socket, ssl
import logging
from urllib.parse import urlparse
import requests
import base64
import re
import signal
import sys
import yaml
import os

class HttpsProxy:
    def __init__(self, config_path='config.yaml'):
        self.load_config(config_path)
        self.running = True
        self.setup_logging()
        self.setup_ssl()
        self.setup_signal_handlers()
        
    def load_config(self, config_path):
        """加载配置文件"""
        # 默认配置
        default_config = {
            'proxy': {
                'source_host': 'z.baidu.com',
                'target_host': 'cn.bing.com',
                'server': {
                    'host': '127.0.0.1',
                    'port': 443
                }
            }
        }
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    if config and 'proxy' in config:
                        self.config = config
                    else:
                        print(f'配置文件 {config_path} 格式不正确，使用默认配置')
                        self.config = default_config
            else:
                print(f'配置文件 {config_path} 不存在，使用默认配置')
                self.config = default_config
                
            # 从配置中提取值
            proxy_config = self.config['proxy']
            self.host = proxy_config['server']['host']
            self.port = proxy_config['server']['port']
            self.target_host = proxy_config['target_host']
            self.host_pattern = proxy_config['source_host']
            
        except Exception as e:
            print(f'加载配置文件时出错: {str(e)}，使用默认配置')
            self.config = default_config
            # 确保在出错时也设置默认值
            self.host = default_config['proxy']['server']['host']
            self.port = default_config['proxy']['server']['port']
            self.target_host = default_config['proxy']['target_host']
            self.host_pattern = default_config['proxy']['source_host']
            
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(level=logging.DEBUG,
                          format='%(asctime)s - %(message)s',
                          filename='proxy.log')
                          
    def setup_ssl(self):
        """设置SSL上下文"""
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.context.verify_mode = ssl.CERT_NONE 
        self.context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")
        
    def setup_signal_handlers(self):
        """设置信号处理器"""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
    def signal_handler(self, signum, frame):
        """处理退出信号"""
        print('\n正在关闭服务器...')
        self.running = False
        try:
            self.bind_socket.close()
        except:
            pass
        print('服务器已关闭')
        # 只在非测试环境下退出
        if not hasattr(self, '_testing'):
            sys.exit(0)
        
    def start(self):
        """启动代理服务器"""
        self.bind_socket = socket.socket()
        self.bind_socket.bind((self.host, self.port))
        self.bind_socket.listen(5)
        print(f'ok: wait a link: https://{self.host}:{self.port}')
        print('按 CTRL+C 退出服务器')
        
        while self.running:
            try:
                # 设置accept超时，这样可以定期检查running状态
                self.bind_socket.settimeout(1)
                try:
                    client_socket, addr = self.bind_socket.accept()
                    self.handle_connection(client_socket, addr)
                except socket.timeout:
                    continue
            except Exception as e:
                if self.running:  # 只在服务器正常运行时记录错误
                    logging.error(f"处理连接时发生错误: {str(e)}")
                
    def handle_connection(self, client_socket, addr):
        """处理单个连接"""
        try:
            client_ssl = self.context.wrap_socket(client_socket, server_side=True)
            request = self.receive_request(client_ssl)
            if request:
                self.process_request(request, client_ssl)
        except ssl.SSLError as e:
            logging.info(f"Non HTTPS request from {addr}")
        except Exception as e:
            logging.error(f"处理请求时发生错误: {str(e)}")
        finally:
            client_socket.close()
            
    def receive_request(self, client_ssl):
        """接收并解析请求"""
        try:
            request = client_ssl.recv(1024)
            request_str = request.decode('utf-8')
            logging.debug("Request: %s", request_str)
            
            if '.png' in request_str:
                return None
                
            # 替换目标主机
            match = re.search(self.host_pattern, request_str)
            if match:
                original_host = match.group()
                request_str = re.sub(self.host_pattern, self.target_host, request_str)
                request = request_str.encode('utf-8')
                
            return request
        except Exception as e:
            logging.error(f"接收请求时发生错误: {str(e)}")
            return None
            
    def connect_to_target(self):
        """连接到目标服务器"""
        try:
            # 创建SSL上下文
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            # 创建普通socket并用SSL上下文包装
            plain_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket = context.wrap_socket(plain_socket, server_hostname=self.target_host)
            server_socket.settimeout(10)
            server_socket.connect((self.target_host, 443))
            return server_socket
        except Exception as e:
            logging.error(f"连接目标服务器失败: {str(e)}")
            return None
            
    def process_request(self, request, client_ssl):
        """处理请求并转发"""
        server_socket = self.connect_to_target()
        if not server_socket:
            return
            
        try:
            server_socket.send(request)
            self.handle_response(server_socket, client_ssl)
        finally:
            server_socket.close()
            
    def handle_response(self, server_socket, client_ssl):
        """处理响应数据传输"""
        connection = Connection(client_ssl, server_socket)
        try:
            while True:
                if not connection.check_client_alive():
                    print("客户端已断开")
                    break
                    
                if not connection.transfer_data():
                    break
        finally:
            connection.close()

class Connection:
    """连接管理类"""
    def __init__(self, client_socket, server_socket):
        self.client = client_socket
        self.server = server_socket
        self.buffer_size = 4096
        self.timeout = 1
        
    def close(self):
        """安全关闭所有连接"""
        try:
            self.client.close()
        except:
            pass
        try:
            self.server.close()
        except:
            pass
            
    def check_client_alive(self):
        """检查客户端连接是否存活"""
        try:
            self.client.setblocking(False)
            data = self.client.recv(1)
            if len(data) == 0:
                return False
        except (ssl.SSLWantReadError, BlockingIOError):
            return True
        except:
            return False
        finally:
            self.client.setblocking(True)
        return True
        
    def transfer_data(self):
        """处理数据传输"""
        self.server.settimeout(self.timeout)
        
        try:
            response = self.server.recv(self.buffer_size)
            if not response:
                return False
                
            if not isinstance(response, bytes):
                try:
                    response_str = response.decode('utf-8')
                except UnicodeDecodeError:
                    response_str = base64.b64encode(response).decode('utf-8')
            else:
                response_str = base64.b64encode(response).decode('utf-8')
                
            logging.debug("Response: %s", response_str)
            
            self.client.send(response)
            print(f'Sent: {len(response)} bytes')
            return True
            
        except socket.timeout:
            return True
        except Exception as e:
            print(f"数据传输错误: {str(e)}")
            return False

if __name__ == '__main__':
    proxy = HttpsProxy()
    proxy.start()
