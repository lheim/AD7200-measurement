# iperf3 measurement script for the Talon AD7200


This repositoy contains two scripts:
- measurement script `mm-wave_measurement.py`
- plotting script `mm-wave_plot.py` using matplotlib

The measurement script starts an iperf3 TCP transmission and logs the following data:
- iperf3 logfile (transmission speed, latency, etc.)
- MCS index
- sector sweep using the modem patch from [nexmon-arc](https://github.com/seemoo-lab/nexmon-arc)
