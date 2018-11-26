import serial
import threading
import binascii
import sys
import time
import socket

#UDP Client application


class SocketThread(threading.Thread):
    
#Simply I have taken port number as 2000, No special meaning to it :-)
    def __init__(self,port_number=5005,host="127.0.0.1"):
        
        self.goOn                 = True

        self.UDP_IP = host
        self.UDP_PORT = port_number
        
        
        # initialize the parent class, This is equivalent to calling the constructor of the parent class
        threading.Thread.__init__(self)
        
        self.socket_handler = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.socket_handler.bind((UDP_IP, UDP_PORT))
        #Setting timeout as five seconds
        self.socket_handler.settimeout(5.0)
        self.start()
    
    
    def run(self):

        while self.goOn:
            #print "sending data to server"
            #self.socket_handler.sendto("Hello World",(self.UDP_IP,self.UDP_PORT))
            
            try:
                # buffer size is 1024 bytes
                data, addr = self.socket_handler.recvfrom(1024)
            except:
                print "timeout while receiving, wait again"
                continue
            
            print "Received: "+ data
            
            #time.sleep(5)
    
    #This function is used for stopping this thread from the main thread
    def close(self):
        self.goOn = False
    
if __name__=="__main__":
    socketThread_object = SocketThread(50007,'')


    print "Interactive mode. Commands:"
#    print "  N to get neighbors count"
#    print "  G to get neighbors"
#    print "  I to inject UDP packet"
#    print "  T to test code block"
    print "  X to exit "
    
    try:
        while(1):
            sys.stdout.flush()
            cmd = raw_input('>> ')
            cmd = cmd.split()
            sys.stdout.flush()
            if cmd[0].upper() == 'N':
                print "sending command get neighbors count"
                sys.stdout.flush()
                outputBufLock = True
                outputBuf += command_get_neighbors;
                outputBufLock  = False

            elif cmd[0].upper() == 'G':
                print "sending command get neighbors command"
                sys.stdout.flush()
                outputBufLock = True
                outputBuf += command_get_neighbors;
                outputBufLock  = False
              
            elif cmd[0].upper() == 'I':
                print "sending command Inject UDP packet"
                sys.stdout.flush()
                outputBufLock = True
                command_inject_udp_packet[0] = len(command_inject_udp_packet) + len(udp_packet_data);
                outputBuf += command_inject_udp_packet+udp_packet_data;
                outputBufLock  = False
              
            elif cmd[0].upper() == 'T':
                print "This block is for testing the feature"
                print command_inject_udp_packet[0]
                print len(udp_packet_data)

            elif cmd[0].upper() == 'X':
              print "exiting..."
              break

            else:
                print "No such command: " + ' '.join(cmd)
    except KeyboardInterrupt:
            socketThread_object.close()
            exit()

    socketThread_object.close()
    sys.exit()
