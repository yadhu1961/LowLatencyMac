#A python script to parse the usbmon and save ack latency as json file.

import serial
import threading
import binascii
import sys
import time
import socket
import struct
import json
import re


print "This is the name of the script: ", sys.argv[1]

# file-output.py
f = open(sys.argv[1],'r')

line_galu = [i.rstrip('\n') for i in f]

f.close()

useful_lines = []
counter = 0;
chip_ack_delay = []
for i in line_galu:
    if(i.split()[3] == 'Bi:1:006:1' or i.split()[3] == 'Bo:1:006:1'):
        if(i.split()[0] == 'ffff88040911d540'):
            useful_lines.append(i)
            counter = counter + 1
    else:
        continue

index = 0
while index < len(useful_lines):
    out_time = int(useful_lines[index].split()[1])
    ack_time = int(useful_lines[index+1].split()[1])
    chip_ack_delay.append(ack_time - out_time)
    index = index+2

print chip_ack_delay[:1000]

file_name = "chip_ack_delay" + re.search(r'\d+', sys.argv[1]).group() + '.json'

f = open(file_name,'w')
f.write(json.dumps(chip_ack_delay[:1000]))
f.close()
