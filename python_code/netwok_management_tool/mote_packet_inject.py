#This python script reads the packets from the serial port, builds the routing table based on them.

import socket
import serial
import threading
import binascii
import sys
import time
from ParserData import ParserData
from Routing import Routing
from UDPPacket import UDPPacket

command_set_dagroot = bytearray([0x7e,0x03,0x43,0x00])

command_get_node_type = bytearray([0x7e,0x03,0x43,0x01])

command_get_neighbor_count = bytearray([0x7e,0x03,0x43,0x02])

command_get_neighbors = bytearray([0x7e,0x03,0x43,0x03])

command_inject_udp_packet = bytearray([0x7e,0x03,0x44,0x00])

ping_packet = bytearray([0x14,0x15,0x92,0x0,0x0,0x0,0x0,0x2,0xf1,0x7a,0x55,0x3a,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x1,0x14,0x15,0x92,0x0,0x0,0x0,0x0,0x2,
0x80,0x0,0x47,0x85,0x5,0xa8,0x0,0xd,0x0,0x1,0x2,0x3,0x4,0x5,0x6,0x7,0x8,0x9])


#I have to convert this ipv6 packet to 6LowPAN packet
ipv6_ping_packet  = [0x60,0x9,0xbe,0x7b,0x0,0x12,0x3a,0x40,0xbb,0xbb,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x1,0xbb,0xbb,0x0,0x0,0x0,0x0,0x0,0x0,0x14,0x15,0x92,0x0,0x0,0x0,0x0,0x2,
0x80,0x0,0x3b,0x3d,0xb,0x9d,0x6,0x60,0x0,0x1,0x2,0x3,0x4,0x5,0x6,0x7,0x8,0x9]

ipv6_udp_packet =   [0x60,0x00,0x00,0x00,0x0,0x12,0x11,0x40,0xbb,0xbb,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x1,0xbb,0xbb,0x0,0x0,0x0,0x0,0x0,0x0,0x14,0x15,0x92,0x0,0x0,0x0,0x0,0x2,
0x80,0x0,0x3b,0x3d,0xb,0x9d,0x6,0x60,0x0,0x1,0x2,0x3,0x4,0x5,0x6,0x7,0x8,0x9]


outputBufLock   = False

outputBuf       = ''

isDAGRoot       = False

isDAOReceived   = False

#Beginning of moteProbe Class definition

class moteProbe(threading.Thread):
    
    def __init__(self,serialport=None):

        # store params
        self.serialport           = serialport

        # local variables
        self.framelength         = 0
        self.busyReceiving       = False
        self.inputBuf            = ''
        self.dataLock            = threading.Lock()
        self.rxByte              = 0
        self.prevByte            = 0
        

        # flag to permit exit from read loop
        self.goOn                 = True
        
        self.parser_data = ParserData()
        
        self.routing_instance = Routing()

        # initialize the parent class
        threading.Thread.__init__(self)

        # give this thread a name
        self.name                 = 'moteProbe@'+self.serialport
        
        try:
            self.serial = serial.Serial(self.serialport,'115200',timeout=1)
        except Exception as err:
            print err

        # start myself
        self.start()
        print "serial thread: "+self.name+" started successfully"
        #======================== thread ==========================================
    
    def run(self):
        while self.goOn: # read bytes from serial port
            #Sending commands to mote
            #Here I am using global variables
            global outputBuf
            global outputBufLock
            if (len(outputBuf) > 0) and not outputBufLock:
                self.serial.write(outputBuf)
                #print ':'.join('{:02x}'.format(x) for x in outputBuf)
                outputBuf = ''

            try:
                self.rxByte = self.serial.read(1)
                if not self.rxByte:
                    continue
                elif (int(binascii.hexlify(self.rxByte),16) == 0x7e) and not self.busyReceiving:
                    self.busyReceiving       = True
                    self.prevByte = self.rxByte
                    continue
            except Exception as err:
                print err
                time.sleep(1)
                break
            else:
                if self.busyReceiving and (int(binascii.hexlify(self.prevByte),16) == 0x7e):
                    #Converting string to integer to make comparison easier
                    self.framelength = int(binascii.hexlify(self.rxByte),16)
                    self.inputBuf           += self.rxByte
                    self.prevByte   = self.rxByte
                    continue
                else:
                    self.inputBuf           += self.rxByte
                    if len(self.inputBuf) == self.framelength:
                        self.busyReceiving = False
                        self._process_inputbuf()
    def _process_inputbuf(self):
        if self.inputBuf[1].upper() == 'P':
            print "This is a packet"
            print ":".join("{:02x}".format(ord(c)) for c in self.inputBuf[2:])
            data = [int(binascii.hexlify(x),16) for x in self.inputBuf]
            data_tuple = self.parser_data.parseInput(data[2:])
            global isDAOReceived
            isDAOReceived = self.routing_instance.meshToLbr_notify(data_tuple)
            #print packet_ipv6['next_header']
        elif self.inputBuf[1] == 'D':
            print "This is debug message"
            print ":".join("{:02x}".format(ord(c)) for c in self.inputBuf[2:])
        elif self.inputBuf[1] == 'R':
            print "This is a command response"
            print ":".join("{:02x}".format(ord(c)) for c in self.inputBuf[2:])
        self.inputBuf = ''
        
    def _process_packet(self,packet):
        print "process_packet_func"

    def _fill_outputbuf(self):
        #When user wants to send some data, data will be pushed to this buffer
        print __name__

    def close(self):
        self.goOn = False

#Thread which continuosly receives data from UDP socket and writes into output buffer
class SocketThread(threading.Thread):
    
    def __init__(self,port_number=8889,host="127.0.0.1"):
        
        self.goOn                 = True

        self.UDP_IP = host
        self.UDP_PORT = port_number
        
        
        # initialize the parent class, This is equivalent to calling the constructor of the parent class
        threading.Thread.__init__(self)
        
        self.socket_handler = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.socket_handler.bind((self.UDP_IP, self.UDP_PORT))
        #Setting timeout as five seconds
        self.socket_handler.settimeout(15)
        self.start()
    
    
    def run(self):
        try:
            while self.goOn:
                #print "sending data to server"
                #self.socket_handler.sendto("Hello World",(self.UDP_IP,self.UDP_PORT))
                # buffer size is 1024 bytes
                try:
                    data, addr = self.socket_handler.recvfrom(1024)
                    data = struct.unpack(H2R_PACKET_FORMAT, data)
                    print ("Control command received: %f" % data)
                    #global outputBuf
                    #global outputBufLock
                    #outputBufLock = True
                    #command_inject_udp_packet[1] = len(command_inject_udp_packet) + len(data)-1;
                    #outputBuf += command_inject_udp_packet+data;
                    #outputBufLock  = False
                except socket.timeout:
                    print "timeout exception"
                    continue
        except KeyboardInterrupt:
            self.close()
    
    #This function is used for stopping this thread from the main thread
    def close(self):
        self.goOn = False
        
        
if __name__=="__main__":
    moteProbe_object    = moteProbe('/dev/ttyUSB0')
    test                = UDPPacket() 
    #socketThread_object = SocketThread()
    
    UDP_IP = "127.0.0.1"
    UDP_PORT = 5005
    
    socket_handler = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    socket_handler.bind((UDP_IP, UDP_PORT))
    #Setting timeout as five seconds
    socket_handler.settimeout(15)
    
    try:
        while(1):
            if(isDAOReceived):
                try:
                    data, addr = socket_handler.recvfrom(1024)
                except socket.timeout:
                    print "timeout exception"
                    time.sleep(2)
                    continue
                except KeyboardInterrupt:
                    moteProbe_object.close()
                    exit()
                print "injecting udp packet by converting lowpan packet"
                sys.stdout.flush()
                test.setData(data)
                tmp = test.getPacket()
                lowpan_packet = moteProbe_object.routing_instance.convert_to_iphc(tmp)
                print type(lowpan_packet[0][1])
                
                str_lowpanbytes = ''.join(chr(i) for i in lowpan_packet[0]+lowpan_packet[1])
                str_lowpanbytes = bytearray(str_lowpanbytes)
                print ':'.join('{:02x}'.format(x) for x in str_lowpanbytes)
                
                outputBufLock = True
                command_inject_udp_packet[1] = len(command_inject_udp_packet) + len(str_lowpanbytes)-1; #Here subtracting one because 0x7e is not included in the length
                outputBuf += command_inject_udp_packet+str_lowpanbytes;
                outputBufLock  = False
            else:
                time.sleep(5)
    except KeyboardInterrupt:
        #socketThread_object.close()
        moteProbe_object.close()
        exit()

    moteProbe_object.close()
    #socketThread_object.close()
    exit()
