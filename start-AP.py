#!/usr/bin/env python3

from threading import Lock, Thread, Event
import subprocess
import argparse
import time
import json
import logging



formatter = "%(asctime)s - %(name)s (%(threadName)-10s) - %(levelname)s - %(message)s"
logger = logging.getLogger(__name__)


'''
------------------------------------------
thread 1:
iperf connection (logged using .json) add waiting time in the beginning to adjust for TCP start

'''
def thread_iperf(sync_event, stop_event, target_ip, interval, length, logname):

    logger.info('Starting Thread 1!')

    # call a subprocess for iperf
    args = ['iperf3', '-c', target_ip, '-i', interval, '-t', length, '-J', '--logfile', '%s_throughput.json' %logname]
    logger.debug(args)

    output = subprocess.Popen(args)

    # set an event every second to notify other threads to save MCS and sweep_dump
    for i in range(0, int(length)):
        sync_event.set() # notify the other threads
        time.sleep(1)


    logger.info('Setting Stop Event!')
    stop_event.set()
    logger.info('Setting Sync Event one last time!')
    sync_event.set() # run one last time

    logger.info('Finished Thread 1!')







'''
------------------------------------------
thread 2:
log MCS with 'iw dev wlan2 link'

'''
def thread_mcs(sync_event, stop_event, logname):

    logger.info('Starting Thread 2!')


    iw_dict = {} # create dict

    i = 0

    while True:

        sync_event.wait() # Blocks until the flag becomes true.

        output = subprocess.check_output(['iw', 'dev', 'wlan2', 'link'])

        output = output.decode()
        timestamp = time.time()

        iw_dict[timestamp] = {}
        iw_dict[timestamp]['interval'] = i
        i += 1

        '''
        example output:
        b'Connected to 04:ce:14:0a:95:ca (on wlan2)\n\tSSID: TALON_AD7200\n\tfreq: 60480\n\tRX: 886905455 bytes (765029 packets)\n\tTX: 490872835 bytes (104713 packets)\n\ttx bitrate: 3080.0 MBit/s MCS 10\n'
        '''

        # filter output and save in a dict
        iw_dict[timestamp]['bitrate'] = output[output.find('bitrate')+9:output.find(' MCS')]
        iw_dict[timestamp]['MCS'] = output[output.find('MCS')+4:-1]



        if sync_event.is_set():
            sync_event.clear() # resets the flag

        if stop_event.is_set():
            break


    # save dict as a json file
    iw_file = open("%s_iw-log.json" %logname,"w+")


    json.dump(iw_dict, iw_file, indent='\t')

    logger.info('Finished Thread 2!')






'''
------------------------------------------
thread 3:
log sector sweep 'cat /sys/kernel/debug/ieee80211/phy2/wil6210/sweep_dump_cur'
'''
def thread_sweep(sync_event, stop_event, logname):

    logger.info('Starting Thread 3!')
    sweeps_log = 'Start sweep_dump log:\n'

    while True:
        sync_event.wait() # Blocks until the flag becomes true.

        try:
            sweep_dump = open("/sys/kernel/debug/ieee80211/phy2/wil6210/sweep_dump_cur","r")

            sweeps_log += sweep_dump.read()


        except IOError:
            logger.warning("Could not open 'sweep_dump_cur'!")


        if sync_event.is_set():
            sync_event.clear() # Resets the flag.

        if stop_event.is_set():
            break

    logger.info('Writing sweep-dump to .json')

    sweep_file = open("%s-sweep-dump.json" %logname, "w+")
    sweep_file.write(sweeps_log) # save the log as raw file. as json processing might take to long, at least for during the measurement.



    logger.info('Finished Thread 3!')






'''
TODO
------------------------------------------
sync_clients:
'''

def sync_client():

    import sys
    from socket import socket, AF_INET, SOCK_DGRAM

    SERVER_IP   = '192.168.8.102'
    PORT_NUMBER = 5000
    SIZE = 1024
    logger.info ("Test client sending packets to IP {0}, via port {1}\n".format(SERVER_IP, PORT_NUMBER))

    mySocket = socket( AF_INET, SOCK_DGRAM )
    myMessage = "Hello!"
    myMessage1 = "42"
    i = 0
    while i < 10:
        mySocket.sendto(myMessage.encode('utf-8'),(SERVER_IP,PORT_NUMBER))
        i = i + 1

    mySocket.sendto(myMessage1.encode('utf-8'),(SERVER_IP,PORT_NUMBER))

    # sys.exit()



def main():
    parser = argparse.ArgumentParser(description='Starting a measurement. Recording everything with iperf3, MCS index, and a sweep dump every second.')


    parser.add_argument('--target', '-c',   help='IP address of iperf3 server', required=True, type=str)
    parser.add_argument('--interval', '-i', help='set length of iperf3 intervals', default='1', type=str)
    parser.add_argument('--length', '-t',   help='length of the measurement in seconds', default='120', type=str)
    parser.add_argument('--logname', '-l',  help='name of the logfile', required=True, type=str)
    parser.add_argument('--verbose', '-v',  help='enable verbose logging')


    args = parser.parse_args()


    # setting up logger
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format=formatter)
    else:
        logging.basicConfig(level=logging.INFO, format=formatter)



    sync_event = Event()
    stop_event = Event()


    threads = []

    threads.append(Thread(target=thread_iperf, args = [sync_event, stop_event, args.target, args.interval, args.length, args.logname]))
    threads[-1].start() # refers to the last element (-2 to the second last)

    threads.append(Thread(target=thread_mcs, args=[sync_event, stop_event, args.logname]))
    threads[-1].start()

    threads.append(Thread(target=thread_sweep, args=[sync_event, stop_event, args.logname]))
    threads[-1].start()


    # join threads
    for thread in threads:
        thread.join()


    logger.info("All threads joined. All done.")

    return 0




if __name__ == "__main__":
    main()
