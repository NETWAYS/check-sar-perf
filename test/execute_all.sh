echo Pagestat
./check_sar_perf.py pagestat

echo CPU
./check_sar_perf.py cpu

echo Memory Util
./check_sar_perf.py memory_util

echo IO transfer
./check_sar_perf.py io_transfer

echo Queueln Load
./check_sar_perf.py queueln_load

echo Swap Util
./check_sar_perf.py swap_util

echo Swap Stat
./check_sar_perf.py swap_stat

echo Task
./check_sar_perf.py task

echo Kernel
./check_sar_perf.py kernel

echo Disk sda
./check_sar_perf.py disk sda
