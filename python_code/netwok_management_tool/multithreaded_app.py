#A python script to communicate with
# the mote.

import serial
import threading
import struct
import binascii

command_set_dagroot = bytearray([0x03,0x43,0x00])

command_get_neighbor_count = bytearray([0x03,0x43,0x01])

command_get_neighbors = bytearray([0x03,0x43,0x01])






















if __name__ == '__main__':
	
	portname = '/dev/ttyUSB1'
	portbaud = '115200'
	serialport = serial.Serial(portname,portbaud)
	
	print "opened port " + portname + " at " + str(portbaud) + " baud"
	sys.stdout.flush()
	
