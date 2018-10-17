#!/usr/bin/env python3

import json, sys, glob, numpy
import matplotlib.pyplot as plt


logs_iperf = glob.glob('data/2oct18/*iperf.json')

for log in logs_iperf:
    json_object = json.load(open(log))
    data_rates = []
    times = []

    for interval in json_object['intervals']:
        data_rate = interval['sum']['bits_per_second']/(1000*1000)
        data_rates.append(data_rate)
        time = interval['sum']['start']
        times.append(time)

    plt.figure(logs_iperf.index(log)) # create a figure for this plot, to late add further subplots
    plot1 = plt.subplot(211)


    #plt.figure(figsize=(16,9), dpi=300)
    plot1.grid(True)
    plot1.bar(times, data_rates)

    #plt.xlabel('Time in s')
    #plt.ylabel('Throughput in Mbit/s')



    #plt.title('%s' %log[log.find('/')+1:log.find('.json')])
    #filename = 'plots/%s_PLOT.pdf' %log[log.find('/')+1:log.find('.json')]
    #plt.savefig(filename)
    #plt.close()


logs_MCS = glob.glob('data/2oct18/*MCS.json')

for log in logs_MCS:
    json_object = json.load(open(log))
    MCS_indexes = []
    intervals = []


    for datapoint in json_object['data']:
        MCS_index = int(datapoint['MCS'])
        MCS_indexes.append(MCS_index)
        interval = datapoint['interval']
        intervals.append(interval)


    plt.figure(logs_MCS.index(log)) # create a figure for this plot, to late add further subplots
    plot2 = plt.subplot(212)

    #p)
    plot2.grid(True)
    plot2.bar(intervals, MCS_indexes)
    #plot1.xlabel('Interval')
    #plot1.ylabel('MCS Index')



    #plt.figure(figsize=(16,9), dpi=300)
    plt.title('%s' %log[log.find('/')+1:log.find('.json')])
    filename = 'plots/%s_PLOT.pdf' %log[log.find('/')+1:log.find('.json')]
    #plt.show()
    plt.savefig(filename)
    #plt.close()


logs_SWEEP = glob.glob('data/2oct18/*sweep-dump.json')

for log in logs_SWEEP:
    json_object = json.load(open(log))
    role = json_object['role']
    time = json_object['start_time']

    intervals = []
    counters = []

    # rssis = numpy.zeros((121, 32))
    rssis =  [[] for _ in range(121)]

    # snrs = numpy.zeros((121, 32))
    snrs =  [[] for _ in range(121)]


    sectors_rssi = []
    sectors_index = []

    for data in json_object['data']:
        interval = int(data['interval'])
        intervals.append(interval)
        counter = data['counter'] # "counter": "3260 swps, 119271 pkts",
        counters.append(counter)


        for dump in data['dump']:
            rssi = float(dump['rssi'])
            rssis[interval].append(rssi) # "rssi": "84680",
            #numpy.append(rssis[interval], rssi)


            snr = dump['snr'] # "snr": "38 qdB (10 dB)",
            snrs[interval].append(snr)
            #numpy.append(snrs[interval], snr)


        rssi_max = max(rssis[interval])
        sectors_rssi.append(rssi_max)
        sectors_index.append(rssis[interval].index(rssi_max))
        #sectors_index.append(numpy.argmax(rssis[interval]))


    fig = plt.figure()
    # fig, ax = plt.subplots()
    ax = plt.subplot(211)

    # ax2= ax.twinx()

    bar_width = 0.35

    opacity = 0.8

    #print(sectors_index)
    #print(sectors_rssi)

    rects1 = ax.bar(intervals, sectors_rssi, width=bar_width,
                    alpha=opacity, color='b',
                    label='RSSI')

    # rects2 = ax2.bar(intervals , sectors_index, width=bar_width,
    #                alpha=opacity, color='r',
    #                label='Sector Index')

                    #+ bar_width

    ax.set_xlabel('Intervals')
    ax.set_ylabel('RSSI')
    # ax2.set_ylabel('Sector Index')

    ax.set_title('RSSI and Sector Index')

    ax.legend()
    # ax2.legend()


    filename = 'plots/%s_PLOT.pdf' %log[log.find('/')+1:log.find('.json')]

    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            if rects.index(rect) % 2 == 0:
                offset = 40000
            else:
                offset = 0
            ax.text(rect.get_x(), 1.01*height+offset,
                    '{}'.format(sectors_index[rects.index(rect)]), ha='center', va='bottom',
                    fontsize=4)


    autolabel(rects1)


    plot2 = plt.subplot(212)

    plot2.bar(intervals, sectors_index, color='r')
    #plot1.xlabel('Interval')
    #plot1.ylabel('MCS Index')


    #plt.figure(figsize=(16,9), dpi=300)


    plt.savefig(filename)
    plt.close()



# plot piechart for sectors
