import socket, ssl
import logging
from urllib.parse import urlparse
import requests
import base64
import re

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(message)s',
                    filename='proxy.log')


bindsocket = socket.socket()
bindsocket.bind(('127.0.0.1', 443)) 
bindsocket.listen(5)

context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.verify_mode = ssl.CERT_NONE 
context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")

print('ok: wait a link: https://127.0.0.1:443')

while True:
    try:
        clientsocket, addr = bindsocket.accept()
        clientsslsocket = context.wrap_socket(clientsocket, server_side=True)
        
        # 接收请求并记录
        request = clientsslsocket.recv(1024)
        request_str = request.decode('utf-8')
        logging.debug("Request: %s", request_str)
        
        if '.png' in request_str:
            pass

        # 解析目标服务器
        hostname = 'www.google.com.hk'
        

        # 定义匹配 Host 地址的正则 
        host_pattern = r'z.baidu.com'

        # 定义要替换的目标地址
        target_host = 'www.google.com.hk'

        # 使用正则匹配出Host地址
        match = re.search(host_pattern, request_str)
        if match:
            original_host = match.group()
            
            # 替换为目标地址
            request_str = re.sub(host_pattern, target_host, request_str)
            request = request_str.encode('utf-8')


        if hostname is None:
            print('你直接访问了127.0.0.1:443 是不正确的，需要先劫持 hosts')
            continue

        port = 443
        
        # 发送请求到目标服务器
        serversocket = ssl.wrap_socket(socket.socket()) 
        serversocket.connect((hostname, port))
        serversocket.send(request)  

        # # 分块接收响应,直到连接关闭
        # response_chunks = []
        # while True:
        #     chunk = serversocket.recv(10)
        #     if not chunk:
        #         break
        #     response_chunks.append(chunk)

        # # 拼接完整响应
        # response = b''.join(response_chunks)

        # 接收响应并记录
        #response = serversocket.recv(44096)
        while True:
            response = serversocket.recv(4096)
            if not response:
                break
            if not isinstance(response, bytes):
                try:
                    response_str = response.decode('utf-8')
                except UnicodeDecodeError:
                   response_str = base64.b64encode(response).decode('utf-8') 
            else:                
                response_str = base64.b64encode(response).decode('utf-8')

            logging.debug("Response: %s", response_str)
            # 返回响应给客户端
            clientsslsocket.send(response)
            print(f'Recv: {len(response)}')
        

        serversocket.close()
        clientsslsocket.close()
    except ssl.SSLError as e:
        # 非HTTPS请求,记录日志并忽略
        logging.info("Non HTTPS request from %s", addr)
        continue
    except ConnectionAbortedError as e:
        logging.info("Non HTTPS request from %s", addr)
        continue
