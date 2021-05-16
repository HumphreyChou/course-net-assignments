###############################################################################
# client-python.py
# Name:
# JHED ID:
###############################################################################

import sys
import socket

SEND_BUFFER_SIZE = 2048

def client(server_ip, server_port):
    """TODO: Open socket and send message from sys.stdin"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((server_ip, server_port))
    except socket.error:
        print('can not connect to server')
        s.close()
        sys.exit(1)
    msg = sys.stdin.read(SEND_BUFFER_SIZE)
    while msg:
        try:
            s.sendall(msg)
        except socket.error:
            print('can not send to server')
            s.close()
            sys.exit(1)
        msg = sys.stdin.read(SEND_BUFFER_SIZE)
    s.close()

def main():
    """Parse command-line arguments and call client function """
    if len(sys.argv) != 3:
        sys.exit("Usage: python client-python.py [Server IP] [Server Port] < [message]")
    server_ip = sys.argv[1]
    server_port = int(sys.argv[2])
    client(server_ip, server_port)

if __name__ == "__main__":
    main()


