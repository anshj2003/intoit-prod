import socket

host = '172.31.24.57'
port = 6969

serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serversocket.bind((host, port))
serversocket.listen(5)

connection, address = serversocket.accept()
print("Connected frok : ", address)
while True:
    data = connection .recv(1024)
    if not data: break

    print(data)
