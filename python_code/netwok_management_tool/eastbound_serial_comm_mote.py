#A python script to communicate with 
# the mote.

import serial
import threading
import binascii
import sys
import time
import socket
import struct
import json

#This commnd includes the prefix and the security key of the 802.15.4 network
command_set_dagroot = bytearray([0x7e,0x1c,0x43,0x00,0x54,0xbb,0xbb,0x00,0x00,0x00,0x00,0x00,0x00,0x01,0x91,0x5b,0xc9,0xf1,0x5c,0x77,0x57,0x89,0x4f,0x4f,0x86,0x15,0xd8,0x14,0x25,0x27])

command_get_neighbor_count = bytearray([0x7e,0x03,0x43,0x01])

command_get_neighbors = bytearray([0x7e,0x03,0x43,0x02])

command_inject_udp_packet = bytearray([0x7e,0x03,0x44,0x00])

command_get_schedule = bytearray([0x7e,0x03,0x43,0x04])

command_add_tx_slot = bytearray([0x7e,0x03,0x43,0x05])

command_add_rx_slot = bytearray([0x7e,0x03,0x43,0x06])

command_reset_board = bytearray([0x7e,0x03,0x43,0x08])

command_get_buff_stat = bytearray([0x7e,0x03,0x43,0xff])

command_test = bytearray([
0xff,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0xee
])

#this is just a temporary hardcoded data, has to be read from
#sockets later
udp_packet_data = "200"

outputBufLock = False

outputBuf     = []

measured_data = {}

payload_length = 0

H2R_PACKET_FORMAT = 'f'
H2R_PACKET_SIZE = struct.calcsize(H2R_PACKET_FORMAT)

#Beginning of moteProbe Class definition

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
        self.data_pkt_size       = 0 

        # flag to permit exit from read loop
        self.goOn                 = True

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
                #time.sleep(0.1)
                break
            else:
                if self.busyReceiving and (int(binascii.hexlify(self.prevByte),16) == 0x7e):
                    #Converting string to integer to make comparison easier
                    self.framelength = int(binascii.hexlify(self.rxByte),16)
                    self.inputBuf           += self.rxByte
                    self.prevByte   = self.rxByte
                    continue
                elif self.busyReceiving:
                    self.inputBuf           += self.rxByte
                    if len(self.inputBuf) == self.framelength:
                        self.busyReceiving = False
                        self._process_inputbuf()
                else:
                    #Do not accumulate bytes if they don't belong to defined packet format
                    continue

    def _process_inputbuf(self):
        if self.inputBuf[1].upper() == 'P':
            curr_packet_time = int(round(time.time() * 1000))
            #print "received packet: "+":".join("{:02x}".format(ord(c)) for c in self.inputBuf[2:]) + " Packet Latency: " + str(curr_packet_time-self.prev_packet_time)
            #print int(data[4]-0x30)
            if self.prev_pkt  == self.inputBuf[2:]:
                print "Duplicate packet"
                self.inputBuf = ''
                return
            print "received data: "+self.inputBuf[2:]+" , Packet Latency: "+str(curr_packet_time-self.prev_packet_time)
            x = curr_packet_time - self.prev_packet_time
            self.latency[1] = self.latency[1] + 1.0
            if self.latency[1] > 1.0:
                x = curr_packet_time - self.prev_packet_time
                self.running_mean(x)
                print "average latency: "+ str(self.latency[0])
            self.prev_packet_time = curr_packet_time
            self.prev_pkt = self.inputBuf[2:]
        elif self.inputBuf[1] == 'D':
            print "debug msg: "+":".join("{:02x}".format(ord(c)) for c in self.inputBuf[2:])
            global measured_data
            global payload_length
            if str(self.data_pkt_size) in measured_data.keys():
                measured_data[str(self.data_pkt_size)].append(int(binascii.hexlify(self.inputBuf[2]),16))
            else:
                measured_data[str(self.data_pkt_size)] = [int(binascii.hexlify(self.inputBuf[2]),16)]
            if(len(measured_data[str(self.data_pkt_size)]) == 300):
                #print measured_data[str(self.data_pkt_size)]
                print(json.dumps(measured_data))
                if payload_length == 0:
                    f = open('measurement_data.json','w')
                    f.write(json.dumps(measured_data))
                    f.close()
                    payload_length = -1
                    self.close()
                else:
                    payload_length = payload_length + 1
        elif self.inputBuf[1] == 'R':
            print "command response: "+":".join("{:02x}".format(ord(c)) for c in self.inputBuf[2:])
        #elif self.inputBuf[1] == 'E' and not (int(binascii.hexlify(self.inputBuf[3]),16) == 0x09) \
                #and not (int(binascii.hexlify(self.inputBuf[3]),16) == 0x1c) :
        elif self.inputBuf[1] == 'E':
            if (int(binascii.hexlify(self.inputBuf[3]),16) == 0x09): #\
                #or (int(binascii.hexlify(self.inputBuf[3]),16) == 0x1c) :
                    print "error msg: "+":".join("{:02x}".format(ord(c)) for c in self.inputBuf[2:])
            else:
                print "------------------------------------------------------------------------"
                print "error msg: "+":".join("{:02x}".format(ord(c)) for c in self.inputBuf[2:])
                print "------------------------------------------------------------------------"
        elif self.inputBuf[1] == 'S':
            #Sending commands to mote
            #Here I am using global variables
            curr_packet_time = int(round(time.time() * 1000))
            #print "request frame: " + str(curr_packet_time-self.rframe_latency)
            self.rframe_latency  =  curr_packet_time
            global outputBuf
            global outputBufLock
            if (len(outputBuf) > 0) and not outputBufLock:
                outputBufLock = True
                dataToWrite = outputBuf.pop(0)
                outputBufLock = False
                print "injecting: "+":".join("{:02x}".format(ord(c)) for c in dataToWrite)
                self.data_pkt_size = len(dataToWrite)
                print len(dataToWrite)
                self.serial.write(dataToWrite)
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
        #I have used 300 to make sure that first outlier is rejected, while calculating the average
        tmp = self.latency[0] * max(self.latency[1]-1,1) + x
        self.latency[0] = tmp / self.latency[1]
#End of ModeProbe class definition



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
                    a = 200
                    #packed_a = struct.pack('f',a)
                    #data, addr = self.socket_handler.recvfrom(1024)
                    #float_data = struct.unpack(H2R_PACKET_FORMAT, data)
                    #print ("Control command received: %f" % a)
                    print "sending: "+"yadhu"
                    global outputBuf
                    global outputBufLock
                    outputBufLock = True
                    command_inject_udp_packet[1] = len(command_inject_udp_packet) + len("yadhu")-1;
                    outputBuf += command_inject_udp_packet+"yadhu";
                    outputBufLock  = False
                    time.sleep(0.1)
                except socket.timeout:
                    print "timeout exception"
                    continue
        except KeyboardInterrupt:
            self.close()
    
    #This function is used for stopping this thread from the main thread
    def close(self):
        self.goOn = False

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
    moteProbe_object    = moteProbe('/dev/ttyUSB1')
    print "Interactive mode. Commands:"
    print "  root to make mote DAGroot"
    print "  inject to inject packet"
    print "  ipv6 to inject one packet"
    print "  sch to get mote schedule"
    print "  tx to add tx slot"
    print "  rx to add rx slot"
    print "  reset to reset the board"
    print "  quit to exit "
    
    #UDP_IP = "127.0.0.1"
    #UDP_PORT = 5006
    
    #socket_handler = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    #socket_handler.bind((UDP_IP, UDP_PORT))
    #Setting timeout as five seconds
    #socket_handler.settimeout(15)
    
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
                str_lowpanbytes = "Yadhunandana"
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
            elif cmd == "test":
                print "sending test command"
                if not outputBufLock:
                    outputBufLock = True
                    outputBuf += [str(command_test)]
                    outputBufLock  = False
            elif cmd == "quit":
                print "exiting"
                break;
            else:
                print "unknown command"
            while(SendPacketMode):
                #try:
                    #a, addr = socket_handler.recvfrom(1024)
                #except socket.timeout:
                    #print "timeout exception"
                    #continue
                #except KeyboardInterrupt:
                    #moteProbe_object.close()
                    #exit()
                if payload_length == -1:
                    exit()
                millis = command_test[:payload_length]
                temp = str(command_test[:payload_length])
                sys.stdout.flush()
                command_inject_udp_packet[1] = len(command_inject_udp_packet) + len(str(millis))-1 + 2;
                chsum = checkSumCalc(bytearray(str(command_inject_udp_packet[1:])+temp))
                if not outputBufLock:
                    outputBufLock = True
                    outputBuf += [str(command_inject_udp_packet)+temp+str(chsum)]
                    outputBufLock  = False
                time.sleep(0.3)
    except KeyboardInterrupt:
        #socketThread_object.close()
        moteProbe_object.close()
        exit()

    moteProbe_object.close()
    #socketThread_object.close()
    exit()
