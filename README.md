check_sar_perf
==============

This plug-in was written to get performance data from sar.
Can be called using NRPE or check\_by\_ssh on remote systems.

You may need to tweak the profiles to be compatible with your version of sysstat. Please make modifications to the myOpts section.

### Requirements

* `sysstat` tool

### Usage

    # ./check_sar_perf.py <profile1> [<profile2> <profile3> ...]

Example:

    check_sar_perf.py cpu
    sar OK| CPU=all user=59.90 nice=0.00 system=4.46 iowait=0.00 steal=0.00 idle=35.64
    
    check_sar_perf.py disk sda
    sar OK| DEV=sda tps=0.00 rd_sec/s=0.00 wr_sec/s=0.00 avgrq-sz=0.00 avgqu-sz=0.00 await=0.00 svctm=0.00 util=0.00
    
    check_sar_perf.py foo
    ERROR: option not defined

### Profiles

* pagestat
* cpu
* memory_util
* memory_stat
* io_transfer
* queueln_load
* swap_util
* swap_stat
* task
* kernel
* disk

