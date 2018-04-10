from socket import socket, AF_INET, SOCK_STREAM


HOST, PORT = 'localhost', 9999

SB = b'\x0B'
EB = b'\x1C\r'

with open('../test/c4800.hl7', 'r') as f:
    data = f.read().replace('\n', '\r').encode()

msg_out = SB + data + EB

s = socket(AF_INET, SOCK_STREAM)
s.connect((HOST, PORT))
s.sendall(msg_out)
resp = s.recv(10240).decode()
print(resp)
s.close()
