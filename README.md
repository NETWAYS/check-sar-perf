check_sar_perf
==============

This is a fork of [nickanderson/check-sar-perf](https://github.com/nickanderson/check-sar-perf)
with some improvements and updates.

This plug-in was written to get performance data from sar.
Can be integrated into Icinga with using the agent. v2.11
provides a CheckCommand definition inside the [ITL](https://icinga.com/docs/icinga2/latest/doc/10-icinga-template-library/).


You may need to tweak the profiles to be compatible with your
version of sysstat. Modifications can be make to the `PROFILES` variable.

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
```

## Examples

```bash
check_sar_perf.py cpu
OK: sar | CPU=all user=59.90 nice=0.00 system=4.46 iowait=0.00 steal=0.00 idle=35.64

check_sar_perf.py disk --device sda
OK: sar | DEV=sda tps=0.00 rd_secs=0.00 wr_secs=0.00 avgrq-sz=0.00 avgqu-sz=0.00 await=0.00

check_sar_perf.py foo
ERROR: check_sar_perf.py: error: argument profile: invalid choice
```

## Profiles

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
