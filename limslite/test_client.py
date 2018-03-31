from socket import socket, AF_INET, SOCK_STREAM


HOST, PORT = 'localhost', 9999
with open('../c4800.hl7', 'r') as f:
    data = f.read().encode()

SB = b'\x0B'
EB = b'\x1C\r'

msg = SB + data + EB

s = socket(AF_INET, SOCK_STREAM)
s.connect((HOST, PORT))
s.sendall(SB + data + b'\r' + EB)
resp = s.recv(10240).decode()
print(resp)
s.close()
