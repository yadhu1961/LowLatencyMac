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
import json
from datetime import datetime

#This command includes the prefix and the security key of the 802.15.4 network
command_set_dagroot = bytearray([0x7e,0x1c,0x43,0x00,0x54,0xbb,0xbb,0x00,0x00,0x00,0x00,0x00,0x00,0x01,0x91,0x5b,0xc9,0xf1,0x5c,0x77,0x57,0x89,0x4f,0x4f,0x86,0x15,0xd8,0x14,0x25,0x27])

command_get_node_type = bytearray([0x7e,0x03,0x43,0x01])

command_get_neighbor_count = bytearray([0x7e,0x03,0x43,0x02])

command_get_neighbors = bytearray([0x7e,0x03,0x43,0x03])

command_get_schedule = bytearray([0x7e,0x03,0x43,0x04])

command_add_tx_slot = bytearray([0x7e,0x03,0x43,0x05])

command_add_rx_slot = bytearray([0x7e,0x03,0x43,0x06])

command_reset_board = bytearray([0x7e,0x03,0x43,0x08])

command_inject_udp_packet = bytearray([0x7e,0x03,0x44,0x00])

ping_packet = bytearray([0x14,0x15,0x92,0x0,0x0,0x0,0x0,0x2,0xf1,0x7a,0x55,0x3a,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x1,0x14,0x15,0x92,0x0,0x0,0x0,0x0,0x2,
0x80,0x0,0x47,0x85,0x5,0xa8,0x0,0xd,0x0,0x1,0x2,0x3,0x4,0x5,0x6,0x7,0x8,0x9])


#I have to convert this ipv6 packet to 6LowPAN packet
ipv6_ping_packet  = [0x60,0x9,0xbe,0x7b,0x0,0x12,0x3a,0x40,0xbb,0xbb,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x1,0xbb,0xbb,0x0,0x0,0x0,0x0,0x0,0x0,0x14,0x15,0x92,0x0,0x0,0x0,0x0,0x2,
0x80,0x0,0x3b,0x3d,0xb,0x9d,0x6,0x60,0x0,0x1,0x2,0x3,0x4,0x5,0x6,0x7,0x8,0x9]

ipv6_udp_packet =   [0x60,0xe,0x30,0x93,0x0,0xb,0x11,0x40,0xbb,0xbb,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x1,0xbb,0xbb,0x0,0x0,0x0,0x0,0x0,0x0,0x14,0x15,0x92,0x0,0x0,0x0,0x0,0x2,
0xa7,0x64,0xf0,0xb2,0x0,0xb,0xe8,0x34,0x31,0x30,0x30]

lowpan_udp_packet = [0xf1,0x7a,0x55,0x11,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x1,0x14,0x15,0x92,0x0,0x0,0x0,0x0,0x2,0xd5,0x9c,0xf0,0xb2,0x0,0xb,0xba,0xc8,0x31,0x30,0x30,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02]

command_test = bytearray([
#0xff,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
#0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
#0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
#0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
#0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
#0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
#0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
#0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0xee
])


outputBufLock   = False

outputBuf       = []

isDAGRoot       = False

RoutingInstanceLock    = False

latency = 0.0
measured_data = []

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
        self.prev_packet_time    = 0
        self.latency             = [0.0,0.0] #Here first element represents prev_latency, and second element represents sample count used to calculate the average latency 
        self.prev_pkt            = None
        self.rframe_latency      = 0
        

        # flag to permit exit from read loop
        self.goOn                 = True
        
        self.parser_data = ParserData()
        
        self.routing_instance = Routing()

        # initialize the parent class
        threading.Thread.__init__(self)

        # give this thread a name
        self.name                 = 'moteProbe@'+self.serialport
        
        try:
            self.serial = serial.Serial(self.serialport,'230400')
        except Exception as err:
            print err

        # start myself
        self.start()
        print "serial thread: "+self.name+" started successfully"
        #======================== thread ==========================================
    
    def run(self):
        while self.goOn: # read bytes from serial port

            try:
                self.rxByte = self.serial.read(1)
                if not self.rxByte:
                    continue
                #print binascii.hexlify(self.rxByte)
                if (int(binascii.hexlify(self.rxByte),16) == 0x7e) and not self.busyReceiving:
                    self.busyReceiving       = True
                    self.prevByte = self.rxByte
                    continue
            except Exception as err:
                print err
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
                    if len(self.inputBuf) >= self.framelength:
                        self.busyReceiving = False
                        self._process_inputbuf()
    def _process_inputbuf(self):
        if self.inputBuf[1].upper() == 'P':
            print len(self.inputBuf)+1
            print "received packet: "+":".join("{:02x}".format(ord(c)) for c in self.inputBuf)
            data = [int(binascii.hexlify(x),16) for x in self.inputBuf]
            data_tuple = self.parser_data.parseInput(data[2:])
            (result,data) = self.routing_instance.meshToLbr_notify(data_tuple)
            if not result:
                if self.prev_pkt  == data[4:]:
                    print "Duplicate packet"
                    self.inputBuf = ''
                    return
                curr_packet_time = int(round(time.time() * 1000))
                temp = []
                temp[:] = [x - 0x30 for x in data[4:]]
                temp = "".join(str(i) for i in temp)
                # print "received data: "+':'.join(str(hex(i)) for i in data[4:])+" , Packet Latency: "+str(curr_packet_time-self.prev_packet_time)
                # print "received data len : "+str(len(data[4:]))
                x = curr_packet_time - int(temp)
                print "latency : " + str(x)
                self.latency[1] = self.latency[1] + 1.0
                self.running_mean(x)
                print "average latency: "+ str(self.latency[0])
                self.prev_pkt = data[4:]
        elif self.inputBuf[1] == 'D':
            print "debug msg: "+":".join("{:02x}".format(ord(c)) for c in self.inputBuf[2:])
            measured_data.append(int(binascii.hexlify(self.inputBuf[2]),16))
            #if(len(measured_data[str(payload_length)]) == 50):
            if(len(measured_data) == 50):
                print(json.dumps(measured_data))
                f = open('measurement_radio_rcv_to_nxt_slot_127.json','w')
                f.write(json.dumps(measured_data))
                f.close()
                payload_length = -1
                self.close()
        elif self.inputBuf[1] == 'R':
            print "command response: "+":".join("{:02x}".format(ord(c)) for c in self.inputBuf[2:])
        elif self.inputBuf[1] == 'E':
            print "------------------------------------------------------------------------"
            print "error msg: "+":".join("{:02x}".format(ord(c)) for c in self.inputBuf[2:])
            print "------------------------------------------------------------------------"
        elif self.inputBuf[1] == 'S':
            #Sending commands to mote
            #Here I am using global variables
            # curr_packet_time = int(round(time.time() * 1000))
            # print "request frame: " + str(curr_packet_time-self.rframe_latency)
            # self.rframe_latency  =  curr_packet_time
            global outputBuf
            global outputBufLock
            #global latency
            if (len(outputBuf) > 0) and not outputBufLock:
                outputBufLock = True
                dataToWrite = outputBuf.pop(0)
                outputBufLock = False
                #print int(round(time.time() * 1000)) - latency
                self.serial.write(dataToWrite)
                #print len(dataToWrite)
                print "injecting: "+":".join("{:02x}".format(ord(c)) for c in dataToWrite)
        self.inputBuf = ''

    def _process_packet(self,packet):
        print "process_packet_func"

    def _fill_outputbuf(self):
        #When user wants to send some data, data will be pushed to this buffer
        print __name__

    def close(self):
        self.goOn = False

    def prepare_UDP_packet(self,payload):
        print "prepare_UDP_packet"

        #Running mean implementation by storing only one element, and sample count
    def running_mean(self,x):
        tmp = self.latency[0] * (self.latency[1]-1) + x
        self.latency[0] = tmp / self.latency[1]
#End of ModeProbe class definition

SendPacketMode = False
def checkSumCalc(pkt):
    p = sum(pkt)
    result = [0,0]
    #Following little endian because it becomes easy in C to convert to value.
    result[1] = p >> 8
    result[0] = p & 0xff
    #print "checksum: "+':'.join('{:02x}'.format(x) for x in result)
    return bytearray(result)


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
    
    print "Interactive mode. Commands:"
    print "  root to make mote DAGroot"
    print "  inject to inject packet"
    print "  ipv6 to inject one packet"
    print "  sch to get mote schedule"
    print "  tx to add tx slot"
    print "  rx to add rx slot"
    print "  reset to reset the board"
    print "  quit to exit "
    
    try:
        while(1):
            sys.stdout.flush()
            cmd = raw_input('>> ')
            sys.stdout.flush()
            if cmd == "root":
                print "sending set DAG root command"
                sys.stdout.flush()
                command_set_dagroot[1] = len(command_set_dagroot)-1 + 2 #excluding 0x7e and including 2 byte checksum in the len
                chsum = checkSumCalc(command_set_dagroot[1:]) #Excluding 0x7e for checksum calculation
                outputBufLock = True
                outputBuf += [str(command_set_dagroot + chsum)];
                outputBufLock  = False
            elif cmd=="inject":
                print "Entering packet inject mode"
                sys.stdout.flush()
                SendPacketMode = True
            elif cmd == "ipv6":
                print "injecting one packet udp packet by converting lowpan packet"
                sys.stdout.flush()
                print len(command_test)
                test.setData(command_test)
                tmp = test.getPacket()
                lowpan_packet = moteProbe_object.routing_instance.convert_to_iphc(tmp)
                if lowpan_packet is None:
                    print "Unable to inject packet"
                    continue
                str_lowpanbytes = ''.join(chr(i) for i in lowpan_packet[0]+lowpan_packet[1])
                #Here subtracting one because 0x7e is not included in the length, Adding to two to include checksum bytes.
                command_inject_udp_packet[1] = len(command_inject_udp_packet) + len(str_lowpanbytes)-1 + 2;
                #Here I will calculate 16-bit checksum for the whole packet then, I will attach it to end of the packet.
                chsum = checkSumCalc(bytearray(str(command_inject_udp_packet[1:])+str_lowpanbytes))
                if not outputBufLock:
                    outputBufLock = True
                    outputBuf += [str(command_inject_udp_packet)+str_lowpanbytes+str(chsum)]
                    outputBufLock  = False
            elif cmd == "sch":
                print "sending get schedule command"
                sys.stdout.flush()
                command_get_schedule[1] = len(command_get_schedule)-1 + 2 #excluding 0x7e and including 2 byte checksum in the len
                chsum = checkSumCalc(command_get_schedule[1:]) #Excluding 0x7e for checksum calculation
                outputBufLock = True
                outputBuf += [str(command_get_schedule + chsum)];
                outputBufLock  = False
            elif cmd == "tx":
                print "sending add tx slot command"
                sys.stdout.flush()
                command_add_tx_slot[1] = len(command_add_tx_slot)-1 + 2 #excluding 0x7e and including 2 byte checksum in the len
                chsum = checkSumCalc(command_add_tx_slot[1:]) #Excluding 0x7e for checksum calculation
                outputBufLock = True
                outputBuf += [str(command_add_tx_slot + chsum)];
                outputBufLock  = False
            elif cmd == "rx":
                print "sending add rx slot command"
                sys.stdout.flush()
                command_add_rx_slot[1] = len(command_add_rx_slot)-1 + 2 #excluding 0x7e and including 2 byte checksum in the len
                chsum = checkSumCalc(command_add_rx_slot[1:]) #Excluding 0x7e for checksum calculation
                outputBufLock = True
                outputBuf += [str(command_add_rx_slot + chsum)];
                outputBufLock  = False
            elif cmd == "reset":
                print "sending reset command"
                sys.stdout.flush()
                command_reset_board[1] = len(command_reset_board)-1 + 2 #excluding 0x7e and including 2 byte checksum in the len
                chsum = checkSumCalc(command_reset_board[1:]) #Excluding 0x7e for checksum calculation
                outputBufLock = True
                outputBuf += [str(command_reset_board + chsum)];
                outputBufLock  = False
            elif cmd == "quit":
                print "exiting"
                break;
            else:
                print "unknown command"
            while(SendPacketMode):
                    #try:
                        #data, addr = socket_handler.recvfrom(3)
                    #except socket.timeout:
                        #print "timeout exception"
                        #continue
                    #except KeyboardInterrupt:
                        #moteProbe_object.close()
                        #exit()
                    millis = int(round(time.time() * 1000))
                    sys.stdout.flush()
                    test.setData(command_test)
                    print len(command_test)
                    tmp = test.getPacket()
                    #print "ipv6: "+':'.join(hex(i) for i in tmp)
                    lowpan_packet = moteProbe_object.routing_instance.convert_to_iphc(tmp)
                    if lowpan_packet is None:
                        #This happens when we don't have a route to the mote
                        print "Unable to inject packet"
                        time.sleep(0.1)
                        continue
                    #str_lowpanbytes = lowpan_udp_packet
                    str_lowpanbytes = ''.join(chr(i) for i in lowpan_packet[0]+lowpan_packet[1])
                    #Here subtracting one because 0x7e is not included in the length, Adding to two to include checksum bytes.
                    command_inject_udp_packet[1] = len(command_inject_udp_packet) + len(str_lowpanbytes)-1 + 2;
                    #Here I will calculate 16-bit checksum for the whole packet then, I will attach it to end of the packet.
                    chsum = checkSumCalc(bytearray(str(command_inject_udp_packet[1:])+str_lowpanbytes))
                    if not outputBufLock:
                        outputBufLock = True
                        outputBuf += [str(command_inject_udp_packet)+str_lowpanbytes+str(chsum)]
                        outputBufLock  = False
                    time.sleep(0.1)
    except KeyboardInterrupt:
        #socketThread_object.close()
        moteProbe_object.close()
        exit()

    moteProbe_object.close()
    #socketThread_object.close()
    exit()
