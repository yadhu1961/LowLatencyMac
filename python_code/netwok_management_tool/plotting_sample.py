#!/usr/bin/python
import numpy as np
import matplotlib.mlab as mlab
import matplotlib.pyplot as plt
import scipy as sp
import scipy.stats
import json
 
#file_ref = open("measurement_udp_data.json","r")

#data = json.load(file_ref)

#file_ref.close()

#sample count is how many samples are taken for any one payload len, any payload length will do.
#sample_count = len(data['6'])
#sample_means = []
#x_axis = []

#for key in data:
    #mean = np.mean(data[key])
    #sample_means.append(mean)
    #x_axis.append(int(key))

#plt.plot(x_axis,sample_means,'bo',label = 'Processing Delay')

#plt.xticks(np.arange(0, 80, 5.0))
#plt.yticks(np.arange(0, 40, 2.0))
#plt.title('UDP Payload length versus Processing delay')
#plt.grid(color='gray', linestyle='dotted')
#plt.xlabel('UDP payload length')
#plt.ylabel('Average ticks taken to process the packet')

#plt.show()
file_ref = open("measurement_serial_data127.json","r")

data127 = json.load(file_ref)

file_ref.close()

file_ref = open("sniffed_data127.json","r")

sniffed_data127 = json.load(file_ref)

file_ref.close()

file_ref = open("measurement_serial_data54.json","r")

data54 = json.load(file_ref)

file_ref.close()

file_ref = open("sniffed_54.json","r")

sniffed_data54 = json.load(file_ref)

file_ref.close()


mean127_measured = np.mean(data127)
mean127_sniffed = np.mean(sniffed_data127)

mean54_measured = np.mean(data54)
mean54_sniffed = np.mean(sniffed_data54)

print "mean127_measured: "+ str (mean127_measured)
print "chip ack delay 127: " + str (mean127_sniffed)
print "uart delay" + str(127*86)


print "mean54_measured: "+ str (mean54_measured)
print "chip ack delay 54: " + str (mean54_sniffed)
print "uart delay" + str(54*86)

for i in range(0,20):
    print (data127[i] - sniffed_data127[i]) - 10 - 86 #This 10 is for pc ACK. 86 for uart tx of last byte

