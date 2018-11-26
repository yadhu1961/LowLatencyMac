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
from sys import argv

#This command includes the prefix and the security key of the 802.15.4 network
command_set_dagroot = bytearray([0x7e,0x1c,0x43,0x00,0x54,0xbb,0xbb,0x00,0x00,0x00,0x00,0x00,0x00,0x01,0x91,0x5b,0xc9,0xf1,0x5c,0x77,0x57,0x89,0x4f,0x4f,0x86,0x15,0xd8,0x14,0x25,0x27])

command_get_neighbor_count = bytearray([0x7e,0x03,0x43,0x02])

command_get_neighbors = bytearray([0x7e,0x03,0x43,0x03])

command_inject_udp_packet = bytearray([0x7e,0x03,0x44,0x00])

command_get_schedule = bytearray([0x7e,0x03,0x43,0x04])

command_add_tx_slot = bytearray([0x7e,0x03,0x43,0x05])

command_add_rx_slot = bytearray([0x7e,0x03,0x43,0x06])

command_reset_board = bytearray([0x7e,0x03,0x43,0x08])

command_get_buff_stat = bytearray([0x7e,0x03,0x43,0xff])

destn_address = bytearray([0x14,0x15,0x92,0x00,0x00,0x00,0x00])

command_test = bytearray([
0xff,
# 0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
# 0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
# 0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
# 0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
# 0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
# 0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
# 0x02,0x02,0x02,0x02,0x02,0x02,0x02,
0x02,0x02,0xee
])

ln1_packet_count = 0
ln2_packet_count = 0

NUM_SAMPLES = 1000
PKT_INTERVAL = 0.025

PAYLOAD_LEN = 77

outputBufLock = False

outputBuf     = []

#Just an initialization for device type.
device_type = "LN1"

measured_data_latency = {}
waiting_time_before_inject  = {}
waiting_time_for_req = 0
prev_sequence_num = -1
packet_loss_count = 0

payload_length = PAYLOAD_LEN

H2R_PACKET_FORMAT = 'f'
H2R_PACKET_SIZE = struct.calcsize(H2R_PACKET_FORMAT)

Am_I_DAGroot = False

is_rf_received = False

#Beginning of moteProbe Class definition

class moteProbe(threading.Thread):

    def __init__(self,serialport='/dev/ttyUSB1'):

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
        global outputBuf
        global outputBufLock
        global waiting_time_for_req
        global waiting_time_before_inject
        global is_rf_received
        global measured_data_latency
        global prev_sequence_num
        global ln1_packet_count
        global packet_loss_count
        if self.inputBuf[1].upper() == 'P':
            curr_packet_time = int(round(time.time() * 1000))
            data = self.inputBuf[2:]
            #print "Payload len: "+ str(len(self.inputBuf[2:]))
            #print "received packet: "+":".join("{:02x}".format(ord(c)) for c in self.inputBuf[2:])
            #print int(data[4]-0x30)
            #if self.prev_pkt  == self.inputBuf[2:]:
                #print "Duplicate packet"
                #self.inputBuf = ''
                #return
            sequence_num = struct.unpack('H',data[:2])[0]
            pkt_gen_time = struct.unpack('l',data[2:])[0]
            latency = curr_packet_time - pkt_gen_time
            print "sequence num: " + str(sequence_num) + " latency : " + str(latency)
            if(device_type == "LN2" or device_type == "LN4"):
                waiting_time_for_req = int(round(time.time() * 1000))
                command_inject_udp_packet[1] = len(command_inject_udp_packet) + len(data)-1 + 8 + 2;
                chsum = checkSumCalc(command_inject_udp_packet[1:]+bytearray(destn_address)+bytearray(data))
                if not outputBufLock:
                    outputBufLock = True
                    outputBuf += [str(command_inject_udp_packet)+str(destn_address)+data+str(chsum)]
                    outputBufLock  = False
                #This is true when packet loss has happened
                if(sequence_num != prev_sequence_num+1):
                    print "packet loss"
                    for i in range(prev_sequence_num+1,sequence_num):
                        measured_data_latency[str(i)] = -1
                        waiting_time_before_inject[str(i)] = -1
                        packet_loss_count +=1
                    #print measured_data_latency
                measured_data_latency[str(sequence_num)] = latency
            else:
                if(sequence_num != prev_sequence_num+1):
                    print "packet loss"
                    for i in range(prev_sequence_num+1,sequence_num):
                        measured_data_latency[str(i)] = -1
                        packet_loss_count +=1
                        #not applicable for leaf node, because this node is injecting packet
                        #hence always packet will be injected
                        #waiting_time_before_inject[str(i)] = -1
                    #print measured_data_latency
                measured_data_latency[str(sequence_num)] = latency
            #x = curr_packet_time - self.prev_packet_time
            #self.latency[1] = self.latency[1] + 1.0
            #if self.latency[1] > 1.0:
                #x = curr_packet_time - self.prev_packet_time
                #self.running_mean(x)
            #self.prev_packet_time = curr_packet_time
            #self.prev_pkt = self.inputBuf[2:]
            prev_sequence_num = sequence_num
            #print "measured latency"
            #print measured_data_latency
            #print "waiting time"
            #print waiting_time_before_inject
        elif self.inputBuf[1] == 'D':
            print "debug msg: "+":".join("{:02x}".format(ord(c)) for c in self.inputBuf[2:])
        elif self.inputBuf[1] == 'A':
            print self.inputBuf[2:]
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
            is_rf_received = True
            #if(not Am_I_DAGroot):
                #temp = str(int(round(time.time() * 1000)))
                #Here subtracting one because 0x7e is not included in the length, Adding to two to include checksum bytes,8 for the address
                #command_inject_udp_packet[1] = len(command_inject_udp_packet) + len(temp)-1 + 8 + 2;
                #Here I will calculate 16-bit checksum for the whole packet then, I will attach it to end of the packet.
                #chsum = checkSumCalc(command_inject_udp_packet[1:]+bytearray(destn_address)+bytearray(temp))
                #if not outputBufLock:
                    #outputBufLock = True
                    #outputBuf += [str(command_inject_udp_packet)+str(destn_address)+temp+str(chsum)]
                    #outputBufLock  = False

            #Sending commands to mote
            #Here I am using global variables
            current_time = int(round(time.time() * 1000))
            #print "request frame: " + str(current_time-self.rframe_latency)
            self.rframe_latency  =  current_time
            if (len(outputBuf) > 0) and not outputBufLock:
                outputBufLock = True
                dataToWrite = outputBuf.pop(0)
                outputBufLock = False
                self.serial.write(dataToWrite)
                if(device_type == "LN2" or device_type == "LN4"):
                    waiting_time_before_inject[str(prev_sequence_num)] = current_time - waiting_time_for_req
                else:
                    if(ln1_packet_count > -1): #to make sure only during injection data is stored
                        waiting_time_before_inject[str(ln1_packet_count)] = current_time - waiting_time_for_req
                #print "injecting: "+":".join("{:02x}".format(ord(c)) for c in dataToWrite)
                print "waiting time before injecting: "+ str(current_time - waiting_time_for_req)
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
#
def checkSumCalc(pkt):
    p = sum(pkt)
    result = [0,0]
    #Following little endian because it becomes easy in C to convert to value.
    result[1] = p >> 8
    result[0] = p & 0xff
    #print "checksum: "+':'.join('{:02x}'.format(x) for x in result)
    return bytearray(result)

SendPacketMode = False

if __name__=="__main__":

    #print(sys.argv)

    if(len(sys.argv) > 1):
        if(sys.argv[1] == "/dev/ttyUSB0"):
            moteProbe_object    = moteProbe(sys.argv[1])
            Am_I_DAGroot = True
            device_type = "DG"
            print device_type
        elif(sys.argv[1] == "/dev/ttyUSB1"):
            moteProbe_object    = moteProbe(sys.argv[1])
            device_type = "LN1"
            destn_address.append(0x03)
            print device_type
        elif(sys.argv[1] == "/dev/ttyUSB2"):
            moteProbe_object    = moteProbe(sys.argv[1])
            device_type = "LN2"
            destn_address.append(0x02)
            print device_type
        elif(sys.argv[1] == "/dev/ttyUSB3"):
            moteProbe_object    = moteProbe(sys.argv[1])
            device_type = "LN3"
            destn_address.append(0x05)
            print device_type
        elif(sys.argv[1] == "/dev/ttyUSB4"):
            moteProbe_object    = moteProbe(sys.argv[1])
            device_type = "LN4"
            destn_address.append(0x04)
            print device_type
    else:
        print "provide serial interface path"
        exit() 

    print "Destn address "+":".join("{:02x}".format(ord(c)) for c in str(destn_address))

    print "Interactive mode. Commands:"
    print "  root to make mote DAGroot"
    print "  inject to inject packet"
    print "  ipv6 to inject one packet"
    print "  sch to get mote schedule"
    print "  tx to add tx slot"
    print "  rx to add rx slot"
    print "  reset to reset the board"
    print "  dump to save a json file"
    print "  quit to exit "

    #UDP_IP = "127.0.0.1"
    #UDP_PORT = 5006

    #socket_handler = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    #socket_handler.bind((UDP_IP, UDP_PORT))
    #Setting timeout as five seconds
    #socket_handler.settimeout(15)
    
    global outputBuf
    global outputBufLock
    global waiting_time_for_req
    global is_rf_received
    global NUM_SAMPLES
    global PKT_INTERVAL
    global packet_loss_count

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
            elif cmd=="nbrs":
                print "get neighbors command"
                sys.stdout.flush()
                command_get_neighbors[1] = len(command_get_neighbors)-1 + 2 #excluding 0x7e and including 2 byte checksum in the len
                chsum = checkSumCalc(command_get_neighbors[1:]) #Excluding 0x7e for checksum calculation
                outputBufLock = True
                outputBuf += [str(command_get_neighbors + chsum)];
                outputBufLock  = False
            elif cmd == "ipv6":
                print "injecting one packet udp packet by converting lowpan packet"
                waiting_time_for_req = int(round(time.time() * 1000))
                temp = struct.pack('l',waiting_time_for_req)
                #Here subtracting one because 0x7e is not included in the length, Adding to two to include checksum bytes,8 for the address
                temp = struct.pack('H',1) + temp
                #Here subtracting one because 0x7e is not included in the length, Adding to two to include checksum bytes,8 for the address
                command_inject_udp_packet[1] = len(command_inject_udp_packet) + len(temp)-1 + 8 + 2;
                #Here I will calculate 16-bit checksum for the whole packet then, I will attach it to end of the packet.
                chsum = checkSumCalc(command_inject_udp_packet[1:]+bytearray(destn_address)+bytearray(temp))
                if not outputBufLock:
                    outputBufLock = True
                    outputBuf += [str(command_inject_udp_packet)+str(destn_address)+temp+str(chsum)]
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
            elif cmd == "dump":
                print "dumping a json file"
                #leaf node case
                if(device_type == "LN1" or device_type == "LN3"):
                    print "packet_delivery ratio: " + str((NUM_SAMPLES - packet_loss_count))
                    print "RTT"
                    print(json.dumps(measured_data_latency))
                    print "waiting time before inject"
                    print(json.dumps(waiting_time_before_inject))
                    file_name1 = "/home/student/iwsn/iwsn_repo/python_code/low_latency_measurements/waiting_time_before_inject_"+ device_type+".json"
                    file_name2 = '/home/student/iwsn/iwsn_repo/python_code/low_latency_measurements/RTT_latency_'+device_type+'.json'
                    f1 = open(file_name1,'w')
                    f2 = open(file_name2,'w')
                    f2.write(json.dumps(measured_data_latency))
                    f1.write(json.dumps(waiting_time_before_inject))
                    f2.close()
                    f1.close()
                elif(device_type == "LN2" or device_type == "LN4"):
                    print "packet_delivery ratio: " + str(NUM_SAMPLES - packet_loss_count)
                    print "one way latency"
                    print(json.dumps(measured_data_latency))
                    print "waiting time before inject"
                    print(json.dumps(waiting_time_before_inject))
                    file_name1 = "/home/student/iwsn/iwsn_repo/python_code/low_latency_measurements/waiting_time_before_inject_"+ device_type+".json"
                    file_name2 = '/home/student/iwsn/iwsn_repo/python_code/low_latency_measurements/oneway_latency_'+device_type+'.json'
                    f1 = open(file_name1,'w')
                    f2 = open(file_name2,'w')
                    f2.write(json.dumps(measured_data_latency))
                    f1.write(json.dumps(waiting_time_before_inject))
                    f2.close()
                    f1.close()
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
                #if payload_length == -1:
                    #exit()
                waiting_time_for_req = int(round(time.time() * 1000))
                temp = struct.pack('l',waiting_time_for_req)
                #Here subtracting one because 0x7e is not included in the length, Adding to two to include checksum bytes,8 for the address
                temp = struct.pack('H',ln1_packet_count) + temp
                #Here subtracting one because 0x7e is not included in the length, Adding to two to include checksum bytes,8 for the address
                command_inject_udp_packet[1] = len(command_inject_udp_packet) + len(temp)-1 + 8 + 2;
                #Here I will calculate 16-bit checksum for the whole packet then, I will attach it to end of the packet.
                chsum = checkSumCalc(command_inject_udp_packet[1:]+bytearray(destn_address)+bytearray(temp))
                #if is_rf_received:
                    #is_rf_received = False
                if not outputBufLock:
                    outputBufLock = True
                    outputBuf += [str(command_inject_udp_packet)+str(destn_address)+temp+str(chsum)]
                    outputBufLock  = False
                ln1_packet_count+=1
                if(ln1_packet_count == NUM_SAMPLES):
                    SendPacketMode = False
                time.sleep(PKT_INTERVAL) #one packet for every 25ms
    except KeyboardInterrupt:
        #socketThread_object.close()
        moteProbe_object.close()
        exit()

    moteProbe_object.close()
    #socketThread_object.close()
    exit()
