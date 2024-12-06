# SuperHttpsMonitor
**超级Https监控**
一些程序并不接受直接进行proxy代理，而一般情况下对此无能为力。
本程序的解决方案有区别于传统的暴力注入，而是通过hosts劫持，然后通过代理服务器进行转发到目标域名，从而实现对目标域名的访问监控。
当然缺点是无法处理当对方检查了证书链的情况。

xxx.exe <=> z.baidu.com <=> hosts <=> 127.0.0.1 <=> SuperHttpsMonitor[成功监控] <=> z.baidu.com


## 使用步骤:
1. 生成自签名证书
2. 在hosts文件中添加 127.0.0.1 [你要劫持的域名]（默认为 z.baidu.com）
3. 配置 config.yaml（可选，有默认配置 z.baidu.com 要与hosts中的域名一致）
4. 运行 run_https_server.py

测试:
`curl "https://z.baidu.com/" -k`


## 配置文件说明
配置文件为 `config.yaml`，格式如下：
```yaml
proxy:
  # 要劫持的源域名
  source_host: z.baidu.com
  # 目标转发域名
  target_host: cn.bing.com
  # 代理服务器配置
  server:
    host: 127.0.0.1
    port: 443
```

如果配置文件不存在或格式不正确，将使用默认配置。

## 运行测试
项目包含完整的单元测试套件，测试覆盖了以下功能：
- 配置文件加载和验证
- 服务器启动和监听
- SSL上下文配置
- 信号处理

运行测试：
```bash
python test_proxy.py
```

测试会自动创建和清理所需的测试文件。所有测试都在独立的环境中运行，不会影响实际的配置文件。
2024年12月6日21:54 周五