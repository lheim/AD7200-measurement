#!/usr/bin/env python3

import json, sys, glob, os
import matplotlib.pyplot as plt

def iperf_mcs_plot(logs_iperf, logs_MCS):
    fig, ax0, ax1, ax2 = [[0 for _ in logs_iperf] for _ in range(4)]
    # interesting: fig = ax0 = ax1 = [0 for _ in logs_iperf] doesnt work.
    # if just an element of the list gets changed, all the others lists inherit this. (fig[0] = 3) -> ax[0] = 3 etc.
    # while when the whole variable is changed, it gets his own memory location

    for index, log in enumerate(logs_iperf):
        json_object = json.load(open(log))
        data_rates = []
        times = []
        rtts = []

        for interval in json_object['intervals']:
            data_rates.append(interval['sum']['bits_per_second']/(1000*1000))
            rtts.append(float(interval['streams'][-1]['rtt'])/1000)
            times.append(interval['sum']['start'])

        # plot iperf performance
        fig[index], (ax0[index], ax1[index], ax2[index]) = plt.subplots(3, 1, sharex=True)

        ax0[index].set_title('iperf3 Throughput')
        ax0[index].grid(True)
        ax0[index].bar(times, data_rates)
        ax0[index].set_ylabel('Throughput in Mbit/s')

        ax1[index].set_title('iperf3 Round-Trip-Time')
        ax1[index].grid(True)
        ax1[index].bar(times, rtts)
        ax1[index].set_ylabel('RTT in ms')


    # MCS logs
    for index, log in enumerate(logs_MCS):
        json_object = json.load(open(log))
        MCS_indexes = []
        intervals = []


        for datapoint in json_object['data']:
            try:
                MCS_index = int(datapoint['MCS'])
            except ValueError:
                MCS_index = -1
            MCS_indexes.append(MCS_index)
            interval = datapoint['interval']
            intervals.append(interval)


        ax2[index].set_title('MCS Index')
        ax2[index].grid(True)
        ax2[index].bar(intervals, MCS_indexes, color='red')
        ax2[index].set_ylabel('MCS Index')

        ax2[index].set_xlabel('Time in s')
        fig[index].subplots_adjust(top=0.95)
        fig[index].suptitle('%s' %log[log.find('/')+1:log.find('.json')], fontsize=4)
        fig[index].tight_layout()


        filename = 'plots/%s_PLOT.pdf' %log[log.find('/')+1:log.find('.json')]
        fig[index].savefig(filename)

def sweep_plot(logs_SWEEP):
    fig, ax0, ax1, ax2, ax3 = [[0 for _ in logs_SWEEP] for _ in range(5)]

    # sweep log
    for index, log in enumerate(logs_SWEEP):
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
        sectors_snr = []
        sectors_index = []

        # loops over the intervals
        for data in json_object['data']:
            interval = int(data['interval'])
            intervals.append(interval)
            counter = data['counter'] # "counter": "3260 swps, 119271 pkts",
            counters.append(counter)

            # loops over the sectors of the individual interval
            for dump in data['dump']:
                rssi = int(dump['rssi'])
                sector = int(dump['sec'])
                rssis[interval].append( (sector, rssi) ) # "rssi": "84680",
                #numpy.append(rssis[interval], rssi)

                snr = dump['snr'] # "snr": "38 qdB (10 dB)",
                snrs[interval].append( (sector, int(snr[0:snr.find('qdB')])) )
                #numpy.append(snrs[interval], snr)

            rssi_max = max(rssis[interval], key=lambda x:x[1])
            sectors_rssi.append( rssi_max )

            snr_max = max(snrs[interval], key=lambda x:x[1])
            sectors_snr.append( snr_max )

            # uncomment for side-by-side comparison of rssi_max and snr_max
            # print(f"rssi_max: {rssi_max} \t\t snr_max: {snr_max}")


        bar_width = 0.35
        opacity = 0.8



        fig[index], (ax0[index], ax1[index], ax2[index], ax3[index]) = plt.subplots(4, 1, sharex=True)

        ax0[index].set_title('RSSI')
        ax0[index].set_ylabel('')
        ax0[index].bar(intervals,
                        [val[1] for val in sectors_rssi],
                        width=bar_width, alpha=opacity, color='b', label='RSSI')


        ax1[index].set_title('SNR')
        ax1[index].set_ylabel('qdB')
        ax1[index].bar(intervals,
                        [val[1] for val in sectors_snr],
                        width=bar_width, alpha=opacity, color='g', label='SNR')


        ax2[index].set_title('Max RSSI Sector')
        ax2[index].set_ylabel('Index')
        ax2[index].bar(intervals, [val[0] for val in sectors_rssi], color='b')


        ax3[index].set_title('Max SNR Sector')
        ax3[index].set_ylabel('Index')
        ax3[index].bar(intervals, [val[0] for val in sectors_snr], color='g')



        ax3[index].set_xlabel('Time in s')
        fig[index].subplots_adjust(top=0.95)
        fig[index].suptitle('%s' %log[log.find('/')+1:log.find('.json')], fontsize=4)
        fig[index].tight_layout()

        filename = 'plots/%s_PLOT.pdf' %log[log.find('/')+1:log.find('.json')]

        fig[index].savefig(filename)

        # creating labels for each bar:
        #
        # def autolabel(rects):
        #     for rect in rects:
        #         height = rect.get_height()
        #         if rects.index(rect) % 2 == 0:
        #             offset = 40000
        #         else:
        #             offset = 0
        #         ax.text(rect.get_x(), 1.01*height+offset,
        #                 '{}'.format(sectors_index[rects.index(rect)]), ha='center', va='bottom',
        #                 fontsize=4)
        #
        #
        # autolabel(rects1)
        #
        #
        # plot2 = plt.subplot(212)
        #
        # plot2.bar(intervals, sectors_index, color='r')
        # #plot1.xlabel('Interval')
        # #plot1.ylabel('MCS Index')
        #
        #
        # #plt.figure(figsize=(16,9), dpi=300)
        #
        #
        # plt.savefig(filename)

if __name__ == "__main__":

    dirs = glob.glob('data/*')
    dir = input(f"Please choose a directory from the following list\n{dirs}\n(For example: {dirs[0][5:]}. If empty, most recent one is taken.):\ndata/")

    if not dir:
        dir = dirs[-1][5:]
        print(f"Using most recent one '{dir}'")


    if not (glob.glob('data/' + dir + '/')):
        print("Directory does not exist or is empty. ✘")
        sys.exit(-1)

    sectors = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,
               59,60,61,62,63]

    logs_iperf = glob.glob('data/' + dir + '/*iperf.json')
    logs_MCS = glob.glob('data/' + dir + '/*MCS.json')
    logs_SWEEP_TX = glob.glob('data/' + dir + '/*TX_sweep-dump.json')
    logs_SWEEP_RX = glob.glob('data/' + dir + '/*RX_sweep-dump.json')

    if not os.path.exists('plots/'+dir):
        print("Directory for plots does not exist yet. Creating it ...")
        os.makedirs('plots/'+dir)
        print("Done.")

    print(f"We got a total of {len(logs_iperf)} IPERF.json's.")
    print(f"We got a total of {len(logs_MCS)} MCS.json's.")
    print(f"We got a total of {len(logs_SWEEP_TX)} SWEEP_TX.json's.")
    print(f"We got a total of {len(logs_SWEEP_RX)} SWEEP_RX.json's.")


    if (len(logs_iperf) == len(logs_MCS) == len(logs_SWEEP_TX) == len(logs_SWEEP_RX)):
        print("Each json has a corresponding partner. ✔")
    else:
        print("Some json's are looking for a partner. :(")


    # sort them by alphabet, to make the ordering match each other
    logs_iperf.sort()
    logs_MCS.sort()
    logs_SWEEP_TX.sort()
    logs_SWEEP_RX.sort()


    iperf_mcs_plot(logs_iperf, logs_MCS)
    sweep_plot(logs_SWEEP_TX)
    sweep_plot(logs_SWEEP_RX)


    print("""
          🌈🌈🌈🌈🌈
          ⭐️ fin ⭐️
          🌈🌈🌈🌈🌈
          """)

    #TODO: plot piechart for sectors
