# Echo server program
import socket
import sys
import time

#UDP echo server application, sends back the received data to client 

UDP_IP = "127.0.0.1"                 # Symbolic name meaning all available interfaces
UDP_PORT = 5005              # Arbitrary non-privileged port
s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
#s.bind((UDP_IP, UDP_PORT))
#s.listen(1)
#conn, addr = s.accept()
#print 'Connected by', addr
try:
    while True:
        #print "waiting for data"
        message = "Sample data"
        #message, address = s.recvfrom(1024)
        #print "Received: "+message+" From: "+address[0]
        #print "this is a tuple: %s" % (address,)
        #print ":".join("{:02x}".format(ord(c)) for c in address)
        #if not message: break
        print "Now sending data"
        s.sendto(message, (UDP_IP, UDP_PORT))
        time.sleep(3)
        
except KeyboardInterrupt:
    exit()
