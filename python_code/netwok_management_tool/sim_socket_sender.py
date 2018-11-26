# Echo server program
import socket
import sys
import time
import struct

#UDP echo server application, sends back the received data to client 

UDP_IP = "bbbb:0:0:0:1415:92cc:0:2"                 # Symbolic name meaning all available interfaces
UDP_PORT = 61618                                    # Arbitrary non-privileged port
s = socket.socket(socket.AF_INET6,socket.SOCK_DGRAM)

counter = 0

try:
    while True:
        counter = counter+1
        print counter
        message = 100
        #millis = int(round(time.time() * 1000))
        print "sending data: "+str(message) +" time: "+str(counter)
        s.sendto(str(message), (UDP_IP, UDP_PORT))
        time.sleep(0.02)
except KeyboardInterrupt:
    exit()
