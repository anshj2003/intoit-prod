import socket


AWAIT_TIMEOUT = 2
class Intoit_Server:
    def __init__(self, addr, port):
        self.ipv4_addr = addr
        self.port = port


        self.serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.serversocket.settimeout(AWAIT_TIMEOUT)
        self.serversocket.bind((self.ipv4_addr, self.port))
        self.serversocket.listen(5)

    def Await_Connection(self):
        try: 
            return self.serversocket.accept()

        except socket.timeout:
            #return None for handling in main thread on timeout so other handling can occur
            return (None, None)


    def Close(self):
        self.serversocket.close()


