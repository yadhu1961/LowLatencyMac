# Echo server program
import socket
import sys
import time
import struct

#UDP echo server application, sends back the received data to client 

UDP_IP = "127.0.0.1"                 # Symbolic name meaning all available interfaces
UDP_PORT = 5005              # Arbitrary non-privileged port
s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)

try:
    while True:
        message = 100
        millis = int(round(time.time() * 1000))
        print "sending data: "+str(message) +" time: "+str(millis)
        s.sendto(str(message), (UDP_IP, UDP_PORT))
        time.sleep(0.083)
except KeyboardInterrupt:
    exit()
