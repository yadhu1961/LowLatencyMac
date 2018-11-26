#!/usr/bin/python
import numpy as np
import matplotlib.mlab as mlab
import matplotlib.pyplot as plt
import binascii
import sys
import json
import re


f = open("log.txt",'r')

line_galu = [i.rstrip('\n') for i in f]

f.close()

useful_lines = []
values = []

for i in line_galu:
    if(i.split()[0] == 'waiting'):
        useful_lines.append(i)
        if(len(i.split()) == 5):
            values.append(int(i.split()[4]))
    else:
        continue


print values

file_name = 'gen_to_inject_waiting_time' + '.json'

f = open(file_name,'w')
f.write(json.dumps(values))
f.close()

# the histogram of the data
n, bins, patches = plt.hist(values, 30, normed=1, facecolor='green', alpha=0.75)

plt.show()




