#!/usr/bin/env python
import numpy as np
import matplotlib.mlab as mlab
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
import scipy as sp
import scipy.stats
import json
import math

def estimate_delay(data_len,delay):
    for i in data_len:
        delay.append((239 + 44.67*float(i) + 5.36*math.floor(i/64))/30.0)
    return

if __name__=="__main__":
    file_ref = open("measurement_data.json","r")

    data = json.load(file_ref)

    file_ref.close()

    #sample count is how many samples are taken for any one payload len, any payload length will do.
    sample_count = len(data['6'])

    confidence_interval_dict = {}
    x_axis = []
    sample_means = []
    list_error_margin = []

    for key in data:
        error_margin = 1.96*(np.std(data[key])/np.sqrt(sample_count))
        mean = np.mean(data[key])
        confidence_interval_dict[key] = [mean,mean-error_margin,mean+error_margin]
        sample_means.append(mean)
        list_error_margin.append((mean-error_margin,mean+error_margin))
        x_axis.append(int(key))

    print confidence_interval_dict
    #print sample_means

    y_error = [(top-bot)/2 for top,bot in list_error_margin]
    
    fig, axs = plt.subplots(nrows=1, ncols=1, sharex=True)
    (_, caps, _) = axs.errorbar(x_axis,sample_means,yerr=y_error, fmt='o',label="""Measured delay mean and
confidence interval(100 samples)""",markersize=2,capsize=2, elinewidth=1)

    x_ticks = np.arange(0, max(x_axis)+1, 5)
    axs.set_xticks(x_ticks)
    y_ticks = np.arange(0,int(max(sample_means))-1, 5)
    axs.set_yticks(y_ticks)
    axs.set_xlabel('Size of serial data')
    axs.set_ylabel('Average ticks')
    axs.grid(which='both')
    axs.grid(color='gray', linestyle='dotted')
    axs.legend()
    for cap in caps:
        cap.set_color('blue')
        cap.set_markeredgewidth(1)
    axs.set_title('Payload versus delay with confidence interval')
    
    delay = []
    error = []

    estimate_delay(x_axis,delay)
    
    for counter,option in enumerate(sample_means):
        error.append(sample_means[counter] - delay[counter])
        
    print np.mean(error)
    
    axs.plot(x_axis,delay,'g.',label = 'Estimated delay',markersize=5)
    axs.plot(x_axis,error,'r.',label = 'Platform specific delay',markersize=5)
    axs.legend()

    plt.show()


