from flask import Flask, request, redirect, session, jsonify, url_for
import os
import socket

app = Flask(__name__)
app.secret_key = os.urandom(24)

host = '127.0.0.1'
port = 5000

serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serversocket.bind((host, port))
serversocket.listen(5)

connection, address = serversocket.accept()
print("Connected frok : ", address)
while True:
    data = connection .recv(1024)
    if not data: break

    print(data)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)