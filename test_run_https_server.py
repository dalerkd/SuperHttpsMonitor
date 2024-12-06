import unittest
import os
import yaml
import socket
import ssl
import threading
import time
import requests
from run_https_server import HttpsProxy

class TestHttpsProxy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """测试开始前的设置"""
        # 创建测试配置文件
        cls.test_config = {
            'proxy': {
                'source_host': 'test.example.com',
                'target_host': 'www.bing.com',
                'server': {
                    'host': '127.0.0.1',
                    'port': 8443
                }
            }
        }
        
        with open('test_config.yaml', 'w') as f:
            yaml.dump(cls.test_config, f)
            
    @classmethod
    def tearDownClass(cls):
        """测试结束后的清理"""
        # 删除测试配置文件
        if os.path.exists('test_config.yaml'):
            os.remove('test_config.yaml')
            
    def setUp(self):
        """每个测试用例开始前的设置"""
        self.proxy = HttpsProxy('test_config.yaml')
        # 标记为测试环境
        self.proxy._testing = True
        # 在新线程中启动代理服务器
        self.server_thread = threading.Thread(target=self.proxy.start)
        self.server_thread.daemon = True
        self.server_thread.start()
        # 等待服务器启动
        time.sleep(1)
        
    def tearDown(self):
        """每个测试用例结束后的清理"""
        self.proxy.running = False
        try:
            # 创建一个连接来触发服务器退出
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('127.0.0.1', 8443))
            sock.close()
        except:
            pass
        self.server_thread.join(timeout=1)
        
    def test_config_loading(self):
        """测试配置文件加载"""
        self.assertEqual(self.proxy.host, '127.0.0.1')
        self.assertEqual(self.proxy.port, 8443)
        self.assertEqual(self.proxy.target_host, 'www.bing.com')
        self.assertEqual(self.proxy.host_pattern, 'test.example.com')
        
    def test_invalid_config(self):
        """测试无效配置处理"""
        # 创建无效配置文件
        with open('invalid_config.yaml', 'w') as f:
            f.write('invalid: yaml: content')
            
        try:
            proxy = HttpsProxy('invalid_config.yaml')
            # 应该使用默认配置
            self.assertEqual(proxy.host, '127.0.0.1')
            self.assertEqual(proxy.port, 443)
            self.assertEqual(proxy.target_host, 'cn.bing.com')
            self.assertEqual(proxy.host_pattern, 'z.baidu.com')
        finally:
            os.remove('invalid_config.yaml')
            
    def test_missing_config(self):
        """测试配置文件缺失的情况"""
        proxy = HttpsProxy('nonexistent_config.yaml')
        # 应该使用默认配置
        self.assertEqual(proxy.host, '127.0.0.1')
        self.assertEqual(proxy.port, 443)
        self.assertEqual(proxy.target_host, 'cn.bing.com')
        self.assertEqual(proxy.host_pattern, 'z.baidu.com')
        
    def test_ssl_context(self):
        """测试SSL上下文配置"""
        self.assertIsInstance(self.proxy.context, ssl.SSLContext)
        self.assertEqual(self.proxy.context.verify_mode, ssl.CERT_NONE)
        
    def test_server_startup(self):
        """测试服务器启动"""
        # 测试服务器是否在监听
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            result = sock.connect_ex(('127.0.0.1', 8443))
            self.assertEqual(result, 0)  # 0 表示连接成功
        finally:
            sock.close()
            
    def test_signal_handling(self):
        """测试信号处理"""
        import signal
        # 测试 SIGTERM 处理
        self.proxy.signal_handler(signal.SIGTERM, None)
        self.assertFalse(self.proxy.running)

def run_tests():
    """运行所有测试"""
    unittest.main(verbosity=2)
    
if __name__ == '__main__':
    run_tests()
