import socket
import ssl
import OpenSSL


# 生成自签名证书
key = OpenSSL.crypto.PKey()
key.generate_key(OpenSSL.crypto.TYPE_RSA, 2048)
cert = OpenSSL.crypto.X509()
cert.set_serial_number(1000)
cert.get_subject().CN = "localhost"
cert.set_issuer(cert.get_subject())
cert.set_pubkey(key)
cert.gmtime_adj_notBefore(0)
cert.gmtime_adj_notAfter(10*365*24*60*60)
cert.sign(key, 'sha256')

with open("cert.pem", "wt") as f:
    f.write(OpenSSL.crypto.dump_certificate(
            OpenSSL.crypto.FILETYPE_PEM, cert).decode())
with open("key.pem", "wt") as f:
    f.write(OpenSSL.crypto.dump_privatekey(
            OpenSSL.crypto.FILETYPE_PEM, key).decode())
