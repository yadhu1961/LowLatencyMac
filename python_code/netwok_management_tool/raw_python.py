# Echo server program
import socket
import sys
import time
import struct

s = socket.socket(socket.AF_INET,socket.SOCK_RAW)
s.bind(("eth0", 0))

try:
    while True:
        message = 1
        s.send(message)
        packet = sock.recv(1)
        print str(packet)
except KeyboardInterrupt:
    exit()
