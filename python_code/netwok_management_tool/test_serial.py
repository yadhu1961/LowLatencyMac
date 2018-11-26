#A python script to communicate with 
# the mote.

import serial
import threading
import binascii
import sys
import time
from datetime import datetime
import json

command_test = bytearray([
0xff,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
0x02,0x02,0x02,0x02,0x02,0x02,0x02,#0x02,0x02,0x02,
0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,
0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0x02,0xee
])
#command_test1 = bytearray([0xff,0x02,0x02,0x02,0xee])
latency = [0.0,0.0]
min_value = 10000000
max_value = 0.0

measured_data = []
payload_length = 1
counter = 0;


def running_mean(x):
    global min_value
    global max_value
    if latency[1] == 1:
        min_value = max_value = x
    else:
        if x < min_value:
            min_value = x
        if x > max_value:
            max_value = x
    #tmp = latency[0] * max(latency[1]-1,1) + x
    #latency[0] = tmp / latency[1]

if __name__=="__main__":
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
        serial = serial.Serial("/dev/ttyUSB0",'115200')
    except Exception as err:
        print err
    counter = 0
    try:
        while(1):
            #sys.stdout.flush()
            #cmd = raw_input('>> ')
            #sys.stdout.flush()
            #if cmd == "test":
                #print "sending test command"
                #a = datetime.now()
                #serial.write(command_test1)
                #try:
                    #rxByte = serial.read(1)
                #except Exception as err:
                    #print err
                #try:
                    #rxByte1 = serial.read(1)
                    #b = datetime.now()
                #except Exception as err:
                    #print err
                #b = datetime.now()
                #c = b - a
                #print c.microseconds
                #print len(command_test1)-1
                #print int(binascii.hexlify(rxByte),16)
                #print int(binascii.hexlify(rxByte1),16)
            #elif cmd == "quit":
                #print "exiting"
                #break;
            #else:
                #print "unknown command"
            a = datetime.now()
            #serial.write(bytearray([0xee]))
            serial.write(command_test[len(command_test)-payload_length:])
            #if counter == 0:
            rxByte = serial.read(1)
            #counter = counter + 1
            b = datetime.now()
            c = b - a
            print "c.microseconds: "+ str(c.microseconds)
            measured_data.append(int(c.microseconds))
            if(counter == 500):
                print measured_data
                file_name = "/home/student/iwsn/iwsn_repo/python_code/new_measurements/measurement_serial_data" + str(payload_length) +".json"
                f = open(file_name,'w')
                f.write(json.dumps(measured_data))
                f.close()
                counter = 0;
                measured_data = []
                if(payload_length < 127):
                    payload_length = payload_length + 1
                    print "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
                    print "new payload_length: " + str(payload_length)
                    print "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
                else:
                    print "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
                    print "exiting"
                    print "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
                    exit()
            #print len(command_test)
            #print int(binascii.hexlify(rxByte),16)
            #latency[1] = latency[1] + 1.0
            #running_mean(c.microseconds)
            #print "latency: "+ str(latency[0])
            #print "max_value: "+ str(max_value)
            #rxByte = serial.read(1)
            counter = counter+1
            #if(counter == 51):
                #print measured_data
                #print json.dumps(measured_data)
                #exit()
            #break
            time.sleep(0.001)
    except KeyboardInterrupt:
        exit()

    exit()

