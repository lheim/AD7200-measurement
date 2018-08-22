#!/usr/bin/env python3

from threading import Lock, Thread, Event
import subprocess
import argparse
import time
import json
import logging
import glob

import sys
from socket import socket, gethostbyname, AF_INET, SOCK_DGRAM



PORT = 5005


formatter = "%(asctime)s - %(name)s (%(threadName)-10s) - %(levelname)s - %(message)s"
logger = logging.getLogger(__name__)


'''
------------------------------------------
thread 1:
iperf connection (logged using .json) add waiting time in the beginning to adjust for TCP start

'''
def thread_iperf_tx(sync_event, stop_event, target_ip, interval, length, logname, reverse):

    logger.info("Starting Thread 'iperf tx'!")

    # call a subprocess for iperf
    args = ['iperf3', '-c', target_ip, '-i', interval, '-t', length, '-J', '--logfile', '%s_TX_iperf.json' %logname]
    if reverse:
        args.append('-R')
    logger.debug(args)

    output = subprocess.Popen(args)

    logger.debug(output)

    notify_receiver(time.time(), target_ip, length, logname, reverse)

    # set an event every second to notify other threads to save MCS and sweep_dump
    for i in range(0, int(length)):
        sync_event.set() # notify the other threads
        time.sleep(1)


    logger.info("Setting Stop Event!")
    stop_event.set()
    logger.debug("Setting Sync Event one last time!")
    sync_event.set() # run one last time

    logger.info("Finished Thread 'iperf tx'!")
    return 0







'''
------------------------------------------
thread 2:
log MCS with 'iw dev wlan2 link'

'''
def thread_mcs(sync_event, stop_event, logname, role):

    logger.info("Starting Thread 'MCS'!")


    iw_dict = {} # create dict


    iw_dict = {}
    iw_dict['filname'] = "%s_MCS.json" %logname
    iw_dict['role'] = role
    iw_dict['start_time'] = time.time()
    iw_dict['data'] = []

    i = 0

    while True:

        sync_event.wait() # Blocks until the flag becomes true.


        iw_dict['data'].append({})
        iw_dict['data'][-1]['time'] = time.time()
        iw_dict['data'][-1]['interval'] = i
        i += 1


        try:
            output = subprocess.check_output(['iw', 'dev', 'wlan2', 'link'])

            '''
            example output:
            b'Connected to 04:ce:14:0a:95:ca (on wlan2)\n\tSSID: TALON_AD7200\n\tfreq: 60480\n\tRX: 886905455 bytes (765029 packets)\n\tTX: 490872835 bytes (104713 packets)\n\ttx bitrate: 3080.0 MBit/s MCS 10\n'
            '''

            output = output.decode()

            logger.debug(output)

            # filter output and save in a dict
            iw_dict['data'][-1]['bitrate'] = output[output.find('bitrate')+9:output.find(' MCS')]
            iw_dict['data'][-1]['MCS'] = output[output.find('MCS')+4:-1]

        except subprocess.CalledProcessError:
            logger.info("Error while checking MCS.")
            iw_dict['data'][-1]['bitrate'] = 'err'
            iw_dict['data'][-1]['MCS'] = 'err'



        if sync_event.is_set():
            sync_event.clear() # resets the flag

        if stop_event.is_set():
            break


    # save dict as a json file
    with open("%s_TX_MCS.json" %logname,"w+") as iw_file:
        json.dump(iw_dict, iw_file, indent='\t')


    logger.info("Finished Thread 'MCS'!")
    return 0







'''
------------------------------------------
thread 3:
log sector sweep 'cat /sys/kernel/debug/ieee80211/phy2/wil6210/sweep_dump_cur'
'''
def thread_sweep(sync_event, stop_event, logname, role):

    logger.info("Starting Thread 'sweep-dump'!")
    sweeps_log = 'Start sweep_dump log:\n'

    i = 0

    sweep_dict = {}
    sweep_dict['filname'] = "%s_sweep-dump.json" %logname
    sweep_dict['role'] = role
    sweep_dict['start_time'] = time.time()
    sweep_dict['data'] = []


    while True:
        sync_event.wait() # Blocks until the flag becomes true.

        try:
            with open("/sys/kernel/debug/ieee80211/phy2/wil6210/sweep_dump_cur", "r") as sweep_dump:

                # sweeps_log += sweep_dump.read()

                first_line = sweep_dump.readline()

                logger.debug("First line %s" %first_line)

                sweep_dict['data'].append({})
                sweep_dict['data'][-1]['time'] = time.time()
                sweep_dict['data'][-1]['interval'] = i;
                sweep_dict['data'][-1]['counter'] = first_line[first_line.find('Counter:')+9:-1].strip()
                sweep_dict['data'][-1]['dump'] = []

                for line in sweep_dump:
                    if line.find('[') is not -1: # skip first and last line
                        logger.debug("Current line %s" %line)
                        sweep_dict['data'][-1]['dump'].append({})
                        sweep_dict['data'][-1]['dump'][-1]['sec'] = line[line.find('sec:')+5:line.find('rssi')-1].strip()
                        sweep_dict['data'][-1]['dump'][-1]['rssi'] = line[line.find('rssi:')+6:line.find('snr')-1].strip()
                        sweep_dict['data'][-1]['dump'][-1]['snr'] = line[line.find('snr:')+5:line.find('src')-1].strip()
                        sweep_dict['data'][-1]['dump'][-1]['src'] = line[line.find('src:')+5:line.find(']')-1].strip()


        except IOError:
            logger.warning("Could not open 'sweep_dump_cur'!")



        i += 1

        if sync_event.is_set():
            sync_event.clear() # Resets the flag.

        if stop_event.is_set():
            break

    logger.debug("Writing sweep-dump to .json")

    with open("%s_sweep-dump.json" %logname, "w+") as sweep_file:
        json.dump(sweep_dict, sweep_file, indent='\t')


    logger.info("Finished Thread 'sweep-dump'!")
    return 0






'''
TODO
------------------------------------------
sync_clients:
'''
def notify_receiver(time, target_ip, length, logname, reversed):

    notificationSocket = socket(AF_INET, SOCK_DGRAM)

    logger.info("Notifying receiver (IP %s via port %d)." %(target_ip, PORT))

    notification = {}
    notification['notifier time'] = time
    notification['length'] = length
    notification['logname'] = logname + '_RX'
    if reversed: #
        notification['role'] = 'tx'
    else:
        notification['role'] = 'rx'

    notificationSocket.sendto(json.dumps(notification).encode('utf-8'), (target_ip, PORT))



def listener_receiver():

    threads = []
    sync_event = Event()
    stop_event = Event()

    SIZE = 1024
    hostName = gethostbyname('0.0.0.0')

    notificationSocket = socket(AF_INET, SOCK_DGRAM)
    notificationSocket.bind((hostName, PORT))

    logger.info("Waiting for notification ...")

    while True:
        (data,addr) = notificationSocket.recvfrom(SIZE)

        try:
            notification = json.loads(data.decode('utf-8'))
        except ValueError:
            Logger.warning("Received faulty data: ValueError.")
            break

        logger.info("Received a notifcation: %s" %notification)

        logger.info("Received time %f:" %notification['notifier time'])
        logger.info("My time %f:" %time.time())



        # SWEEP thread
        threads.append(Thread(target=thread_sweep, args=[sync_event, stop_event, notification['logname'], notification['role']]))
        threads[-1].start()


        # set event
        # set an event every second to notify other threads to save MCS and sweep_dump
        for i in range(0, int(notification['length'])):
            sync_event.set() # notify the other threads
            time.sleep(1)

        logger.info("Setting Stop Event!")
        stop_event.set()
        logger.debug("Setting Sync Event one last time!")
        sync_event.set() # run one last time

        for thread in threads:
            thread.join()

        stop_event.clear()
        logger.info("Threads joined - finished handling notifcation. Waiting for a new notification ...")





def main():
    parser = argparse.ArgumentParser(description="Starting a measurement. Recording everything with iperf3, MCS index, and a sweep dump every second.")


    parser.add_argument('--role', '-r',  help="set the role (transmitter or receiver)", choices=['tx', 'rx'], required=True)


    parser.add_argument('--target', '-c',   help="IP address of iperf3 server", required=True, type=str)
    parser.add_argument('--interval', '-i', help="set length of iperf3 intervals", default='1', type=str)
    parser.add_argument('--length', '-t',   help="length of the measurement in seconds", default='120', type=str)
    parser.add_argument('--logname', '-l',  help="name of the logfile", required=True, type=str)
    parser.add_argument('--reverse', '-R',  help="reverse the direction of the iperf test (server sends)", action='store_true')



    parser.add_argument('--verbose', '-v',  help="enable verbose logging", action='store_true')


    args = parser.parse_args()


    # setting up logger
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format=formatter)
    else:
        logging.basicConfig(level=logging.INFO, format=formatter)


    # check if file already exists
    if glob.glob('%s*' %args.logname):
        logger.warning("Group of files starting with '%s' already exist!" %args.logname)
        return -1



    if args.role == 'tx':

        threads = []
        sync_event = Event()
        stop_event = Event()
        # MCS
        threads.append(Thread(target=thread_mcs, args=[sync_event, stop_event, args.logname, args.role]))
        threads[-1].start()

        # SWEEP
        threads.append(Thread(target=thread_sweep, args=[sync_event, stop_event, args.logname+'_TX', args.role]))
        threads[-1].start()

        # IPERF TX
        threads.append(Thread(target=thread_iperf_tx, args=[sync_event, stop_event, args.target, args.interval, args.length, args.logname, args.reverse]))
        threads[-1].start()


        # join threads
        for thread in threads:
            thread.join()
        logger.info("All threads joined. All done.")



    elif args.role == 'rx':
        logger.info("Please run 'iperf3 -s' on the rx side manually.")
        logger.info("Starting a listener ...")
        try:
            listener_receiver()
        except KeyboardInterrupt:
            logger.info("Keyboard Interrupt: Exiting ...")
            sys.exit()
        # start scripts with different logname get logname from control signal

    else:
        logger.warning("Role not specified.")


    return 0




if __name__ == "__main__":
    main()
