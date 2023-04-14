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

# Safe import for adding sys.exit
try:
    import argparse
    import os
    import sys
    import re
    import subprocess
# pylint: disable=broad-exception-caught
except Exception as import_error: # pragma: no cover
    print(f"UNKNOWN: Failure during import. {import_error}")
    # pylint: disable=consider-using-sys-exit
    exit(3)

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

__version__ = '0.1.0'


# Profiles may need to be modified for different versions of the sysstat package
# This would be a good candidate for a config file
PROFILES = {
    'pagestat': 'sar -B 1 1',
    'cpu': 'sar 1 1',
    'memory_util': 'sar -r 1 1',
    'io_transfer': 'sar -b 1 1',
    'queueln_load': 'sar -q 1 1',
    'swap_util': 'sar -S 1 1',
    'swap_stat': 'sar -W 1 1',
    'task': 'sar -w 1 1',
    'kernel': 'sar -v 1 1',
    'disk': 'sar -d -p 1 1',
}

def commandline(arguments):
    """
    Command Line Interface Function for easier testing
    """
    parser = argparse.ArgumentParser(description="This plugin reads output from sar (sysstat), checks it against thresholds and reports the results (including perfdata)")

    parser.add_argument('-V', '--version',
                        action='version',
                        version='%(prog)s v' + __version__)

    parser.add_argument('profile',
                        choices=PROFILES.keys(),
                        type=str,
                        help='sar Profile to execute for the check.',
                        nargs=1)

    parser.add_argument('-d', '--device',
                        help='Name of the device if the disk profile is selected.',
                        required='disk' in arguments)

    return parser.parse_args(arguments)


class SarNRPE:
    '''
    Call sar and parse statistics returning in NRPE format
    '''
    def __init__(self, command, device=None):
        # tell sar to use the posix time formatting to stay safe
        self.stats = []

        command = 'LC_TIME="POSIX" ' + command
        with subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as sar:
            (sout, _) = sar.communicate()
            sout = sout.decode()

        if device:
            (columns, data) = sort_combined_output(sout, device)
        else:
            (columns, data) = sort_output(sout)

        if data:
            self.formatter(columns, data)

    def formatter(self, columns, data):
        '''
        Construct nrpe format performance data
        '''
        search = re.compile('^[a-zA-Z]+$')
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

    # Initialize return data
    ret_column= []
    ret_data= []

    # Split and remove empty lines
    # Return if result is empty
    lines = [l for l in sarout.split('\n') if l]
    if len(lines) < 2:
        return (ret_column, ret_data)

    # First line contains uname info
    # Second line contains columns
    # The last line the average data
    column = lines[1].split()
    data = lines[-1].split()
    # Remove first element (e.g. Average or timestamp)
    column.pop(0)
    data.pop(0)

    ret_column = column
    ret_data = data

    return (ret_column, ret_data)


def sort_combined_output(sarout, device):
    '''
    Sorts column and data output from combined report and displays
    only relevant information returns column and data tuple
    '''
    # Initialize return data
    ret_column= []
    ret_data= []

    # Split and remove empty lines
    # Return if result is empty
    lines = [l for l in sarout.split('\n') if l]
    if len(lines) < 2:
        return (ret_column, ret_data)

    # First line contains uname info
    # Second line contains columns
    columns = lines[1]
    # Find the only Average line with the device we are looking for
    lines_dev = [l for l in lines if l.startswith("Average:") and device in l]

    if columns:
        ret_column = columns.split()
        ret_column.pop(0)
    if lines_dev:
        ret_data = lines_dev[0].split()
        ret_data.pop(0)

    return (ret_column, ret_data)


def main(args):
    """
    Main function
    """
    if not check_bin('sar'):
        print(f"ERROR: sar not found in $PATH ({os.environ['PATH']}), please install sysstat.")
        return ERR_CRIT

    # Positional args are a list
    args.profile = args.profile[0]

    try:
        if args.profile == 'disk':
            sar = SarNRPE(PROFILES[args.profile], args.device)
        else:
            sar = SarNRPE(PROFILES[args.profile])
    except Exception as sar_error:
        print(f"UNKNOWN: Error running sar. {sar_error}")
        return ERR_UNKN

    # Output in NRPE format
    if sar.stats:
        print('OK: sar |', ' '.join(sar.stats))
        return ERR_OK

    print("UNKNOWN: Could not determine sar perfdata.")
    return ERR_UNKN


if __name__ == '__main__': # pragma: no cover
    try:
        ARGS = commandline(sys.argv[1:])
        sys.exit(main(ARGS))
    except Exception as main_error:
        print(f"UNKNOWN: Error running main(). {main_error}")
        sys.exit(ERR_UNKN)
