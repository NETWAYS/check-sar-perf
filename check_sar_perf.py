#!/usr/bin/env python3
# Copyright (c) 2010, Nick Anderson <nick@cmdln.org>
# Copyright (c) 2012, Michael Friedrich <michael.friedrich@gmail.com>
# All rights reserved.
#
# Modified 2012-07-11 by Michael Friedrich <michael.friedrich@univie.ac.at>
#
# sar uses the locale time in order to format the output
# previously, the plugin matched only
#   04:13:43 PM  pgpgin/s pgpgout/s   fault/s  majflt/s  pgfree/s pgscank/s pgscand/s pgsteal/s    %vmeff
#   04:13:44 PM  17664.00  12672.00     52.00      0.00  11394.00      0.00      0.00      0.00      0.00
# which does not work with the default format
#   16:13:16     pgpgin/s pgpgout/s   fault/s  majflt/s  pgfree/s pgscank/s pgscand/s pgsteal/s    %vmeff
#   16:13:17     13952.00  73640.00     36.00      0.00  10970.00      0.00      0.00      0.00      0.00
# since all systems should share the same, the command is instrumented using POSIX
# time formatting, which makes it work on both ends again.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import sys
import re
import subprocess
import traceback


os.environ['PATH'] = '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/bin'
# Nagios return code level
# 0 - OK       - The plugin was able to check the service and it appeared to be functioning properly
# 1 - WARNING  - The plugin was able to check the service, but it appeared to be above some "warning"
#                threshold or did not appear to be working properly
# 2 - CRITICAL - The plugin detected that either the service was not running or it was above some "critical" threshold
# 3 - UNKNOWN  - Invalid command line arguments were supplied to the plugin or low-level failures
#                internal to the plugin (such as unable to fork, or open a tcp socket) that prevent
#                it from performing the specified operation. Higher-level errors (such as name
#                resolution errors, socket timeouts, etc) are outside of the control of plugins and
#                should generally NOT be reported as UNKNOWN states.
ERR_OK = 0
ERR_WARN = 1
ERR_CRIT = 2
ERR_UNKN = 3

DESCRIPTION = """
check_sar_perf.py
This plugin reads output from sar (sysstat), checks it against thresholds
and reports the results (including perfdata)
"""


def usage():
    '''
    Just print usage
    '''
    print(DESCRIPTION)
    return ERR_UNKN


class SarNRPE:
    '''
    Call sar and parse statistics returning in NRPE format
    '''
    def __init__(self, command, device=None):
        # tell sar to use the posix time formatting to stay safe
        command = 'LC_TIME="POSIX" ' + command
        with subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as sar:
            (sout, _) = sar.communicate()
            sout = sout.decode()
        # == debug
        # print(sout)
        # print("Type: " + str(type(sout)))
        if device is None:
            (columns, data) = sort_output(sout)
        else:
            (columns, data) = sort_combined_output(sout, device)

        self.formatter(columns, data)

    def formatter(self, columns, data):
        '''
        Construct nrpe format performance data
        '''
        search = re.compile('^[a-zA-Z]+$')
        self.stats = []
        # Create dictionary
        for (idx, element) in enumerate(columns):
            # debug
            # print(columns[i], ": ", data[i])
            # Remove first column if data contains only letters
            if idx != 0 or not search.match(data[idx]):
                # Remove characters that cause issues (%/)
                badchars = ['%', '/']
                columns[idx] = ''.join(j for j in element if j not in badchars)
                string = element.strip('%/') + "=" + data[idx].strip()
                # ==debug
                # print(string)
                self.stats.append(string)
                # debug
                # print("Appended data: ", data[i])


def check_bin(program):
    '''
    Ensure the program exists in the PATH
    '''
    for path in os.environ.get('PATH', '').split(':'):
        if os.path.exists(os.path.join(path, program)) and \
           not os.path.isdir(os.path.join(path, program)):
            return os.path.join(path, program)
    return False


def sort_output(sarout):
    '''
    Sort output of sar command, return column and data tuple
    '''
    # print(sarout)
    data = sarout.split('\n')[-2].split()
    # remove 'Average:'
    data.pop(0)
    # debug
    # print(data)
    columns = sarout.split('\n')[-4].split()
    # Remove Timestamp - 16:13:16
    columns.pop(0)
    # timestamp is posix, so no AM or PM
    # debug
    # print(columns)
    return (columns, data)


def sort_combined_output(sarout, device):
    '''
    Sorts column and data output from combined report and displays
    only relevant information returns column and data tuple
    '''

    find_columns = True
    mycolumns = []
    mydata = []
    # Find the column titles
    search = re.compile('^Average:')
    for line in sarout.split('\n'):
        if search.match(line):
            if find_columns:
                mycolumns.append(line)
                find_columns = False
            else:
                mydata.append(line)
    # Find the only Average line with the device we are looking for
    search_string = f'^Average:\\s+.*{device}\\s*.*'
    search = re.compile(search_string)
    for line in mydata[:]:
        if not search.match(line):
            mydata.remove(line)
    mycolumns = mycolumns[0].split()
    mydata = mydata[0].split()
    mycolumns.pop(0)
    mydata.pop(0)
    return (mycolumns, mydata)


def main(args):
    """
    Main function, execute checks, fetch data and so on.
    Maybe just integrate this in the starter function
    """
    # Ensure a profile (aka my_opts) is selected
    if len(args) <= 1:
        print('ERROR: no profile selected')
        return usage()
    if not check_bin('sar'):
        print(f"ERROR: sar not found on PATH ({os.environ['PATH']}), install sysstat")
        return ERR_CRIT

    # Profiles may need to be modified for different versions of the sysstat package
    # This would be a good candidate for a config file
    my_opts = {}
    my_opts['pagestat'] = 'sar -B 1 1'
    my_opts['cpu'] = 'sar 1 1'
    my_opts['memory_util'] = 'sar -r 1 1'
    my_opts['io_transfer'] = 'sar -b 1 1'
    my_opts['queueln_load'] = 'sar -q 1 1'
    my_opts['swap_util'] = 'sar -S 1 1'
    my_opts['swap_stat'] = 'sar -W 1 1'
    my_opts['task'] = 'sar -w 1 1'
    my_opts['kernel'] = 'sar -v 1 1'
    my_opts['disk'] = 'sar -d -p 1 1'

    # If profile uses combined output you must pick one device to report on ie sda for disk
    if args[1] in my_opts:
        if args[1] == 'disk':
            if len(args) > 2:
                sar = SarNRPE(my_opts[args[1]], args[2])
            else:
                print('ERROR: no device specified')
                return ERR_UNKN
        else:
            sar = SarNRPE(my_opts[args[1]])
    else:
        print('ERROR: option not defined')
        return ERR_UNKN

    # Output in NRPE format
    print('sar OK |', ' '.join(sar.stats))

    return ERR_OK


if __name__ == '__main__':
    try:
        result = main(sys.argv)
    except Exception:
        traceback.print_exc()
        print(sys.exc_info())
        print('Unexpected Error')
        sys.exit(ERR_UNKN)
    sys.exit(result)
