check_sar_perf
==============

This is a fork of [nickanderson/check-sar-perf](https://github.com/nickanderson/check-sar-perf)
with some improvements and updates.

This plug-in was written to get performance data from sar.
Can be integrated into Icinga with using the agent. v2.11
provides a CheckCommand definition inside the [ITL](https://icinga.com/docs/icinga2/latest/doc/10-icinga-template-library/).

## Requirements

* `sysstat` tool

## Usage

```bash
usage: check_sar_perf.py [-h] [-V] [-d DEVICE]
                         {pagestat,cpu,memory_util,io_transfer,queueln_load,swap_util,swap_stat,task,kernel,disk}

This plugin reads output from sar (sysstat), checks it against thresholds and reports the results
(including perfdata)

positional arguments:
  {pagestat,cpu,memory_util,io_transfer,queueln_load,swap_util,swap_stat,task,kernel,disk}
                        sar Profile to execute for the check.

options:
  -h, --help            show this help message and exit
  -V, --version         show program's version number and exit
  -d DEVICE, --device DEVICE
                        Name of the device if the disk profile is selected.
  -c CMD, --cmd CMD     Custom sar command to execude. Use as own risk.
```

## Examples

```bash
# CPU Perfdata
check_sar_perf.py cpu
OK: sar | CPU=all user=59.90 nice=0.00 system=4.46 iowait=0.00 steal=0.00 idle=35.64

# Disk 'sda' Perfdata
check_sar_perf.py disk --device sda
OK: sar | DEV=sda tps=0.00 rd_secs=0.00 wr_secs=0.00 avgrq-sz=0.00 avgqu-sz=0.00 await=0.00

# Custom Perdata
check_sar_perf.py custom --cmd "sar -P 1 1 1"
OK: sar | DEV=sda tps=0.00 rd_secs=0.00 wr_secs=0.00 avgrq-sz=0.00 avgqu-sz=0.00 await=0.00

# Custom Perdata with Error
check_sar_perf.py custom --cmd "uptime"
UNKNOWN: Could not determine sar perfdata.

# Invalid input
check_sar_perf.py foo
ERROR: check_sar_perf.py: error: argument profile: invalid choice
```

## Profiles

These profiles are available out-of-the-box:

* pagestat
* cpu
* memory_util
* io_transfer
* queueln_load
* swap_util
* swap_stat
* task
* kernel
* disk

A custom `sar` command can be specified with the `custom` profile and the `--cmd` flag.
