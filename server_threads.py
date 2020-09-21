import socket
import os
from threading import Thread
import os.path

import tqdm


SEPARATOR = "<SEPARATOR>"

clients = []
files = {}
lastfilename = ""

# Thread to listen one particular client
class ClientListener(Thread):
    def __init__(self, name: str, sock: socket.socket):
        super().__init__(daemon=True)
        self.sock = sock
        self.name = name

    # add 'me> ' to sended message
    def _clear_echo(self, data):
        # \033[F – symbol to move the cursor at the beginning of current line (Ctrl+A)
        # \033[K – symbol to clear everything till the end of current line (Ctrl+K)
        self.sock.sendall('\033[F\033[K'.encode())
        data = 'me> '.encode() + data
        # send the message back to user
        self.sock.sendall(data)

    # broadcast the message with name prefix eg: 'u1> '
    def _broadcast(self, data):
        data = (self.name + '> ').encode() + data
        for u in clients:
            # send to everyone except current client
            if u == self.sock:
                continue
            u.sendall(data)

    # clean up
    def _close(self):
        #print("HERE")
        clients.remove(self.sock)
        self.sock.close()
        print(self.name + ' disconnected')

    def run(self):
        while True:
            # try to read 1024 bytes from user
            # this is blocking call, thread will be paused here
            data = self.sock.recv(4096)
            if data:
                received = data.decode()
                if(received=='ASKNAME' or received.find('ASKNAME')!=-1):
                    self.sock.sendall(('Saved on server as '+lastfilename).encode())
                else:
                    filename, filesize = received.split(SEPARATOR)
                    filename = os.path.basename(filename)
                    filesize = int(filesize)
                    #self._clear_echo(data)
                    #self._broadcast(data)
                    if filename in files.keys():
                        files[filename]+=1
                        filename = filename[:filename.find('.')] + '_copy' + str(files[filename]-1) + filename[filename.find('.'):]
                    else:
                        files[filename] = 1
                    lastfilename = filename
                    progress = tqdm.tqdm(range(filesize), f"Receiving {filename}", unit="B", unit_scale=True, unit_divisor=1024)
                    with open(filename, "wb") as f:
                        for _ in progress:
                            # read 1024 bytes from the socket (receive)
                            bytes_read = self.sock.recv(4096)
                            if(bytes_read.decode()=='ASKNAME' or bytes_read.decode().find('ASKNAME')!=-1):
                                self.sock.sendall(('Saved on server as '+lastfilename).encode())
                            if not bytes_read:
                                break
                            # write to the file the bytes we just received
                            f.write(bytes_read)
                            # update the progress bar
                            progress.update(len(bytes_read))
            else:
                # if we got no data – client has disconnected
                self._close()
                # finish the thread
                return


def main():
    next_name = 1

    # AF_INET – IPv4, SOCK_STREAM – TCP
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # reuse address; in OS address will be reserved after app closed for a while
    # so if we close and imidiatly start server again – we'll get error
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # listen to all interfaces at 8800 port
    sock.bind(('', 8080))
    sock.listen()
    
    while True:
        # blocking call, waiting for new client to connect
        con, addr = sock.accept()
        clients.append(con)
        name = 'u' + str(next_name)
        next_name += 1
        print(str(addr) + ' connected as ' + name)
        # start new thread to deal with client
        ClientListener(name, con).start()
    


if __name__ == "__main__":
    main()