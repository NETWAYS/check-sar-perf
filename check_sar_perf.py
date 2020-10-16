#!/usr/bin/env python2
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
from subprocess import *


os.environ['PATH'] = '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/bin'
#Nagios return code level
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

class SarNRPE:
    '''Call sar and parse statistics returning in NRPE format'''
    def __init__(self, command, device=None):
	# tell sar to use the posix time formatting to stay safe
	command = 'LC_TIME="POSIX" '+command
        sar=Popen(command, shell=True, stdout=PIPE, stderr=PIPE)
        (sout,serr) = sar.communicate()
	### debug
	#print sout
        if device == None:
            (columns, data) = self.SortOutput(sout)
        else:
            (columns, data) = self.SortCombinedOutput(sout, device)

        self.Formatter(columns, data)

    def SortOutput(self, sarout):
        '''Sort output of sar command, return column and data tuple'''
        data = sarout.split('\n')[-2].split()
        # remove 'Average:'
        data.pop(0)
	### debug
	#print data
        columns = sarout.split('\n')[-4].split()
	# Remove Timestamp - 16:13:16
        columns.pop(0)
	# timestamp is posix, so no AM or PM
	### debug
	#print columns
        return (columns, data)

    def SortCombinedOutput(self, sarout, device):
        '''Sorts column and data output from combined report and displays
        only relevant information returns column and data tuple'''
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
        search = re.compile('^Average:\s.*%s\s.*' %device)
        for line in mydata[:]:
            if not search.match(line):
                mydata.remove(line)
        mycolumns = mycolumns[0].split()
        mydata = mydata[0].split()
        mycolumns.pop(0)
        mydata.pop(0)
        return (mycolumns,mydata)

    def Formatter(self, columns, data):
        '''Construct nrpe format performance data'''
        search = re.compile('^[a-zA-Z]+$')
        self.stats = []
        # Create dictionary
        for i in range(len(columns)):
	    # debug
	    # print columns[i], ": ", data[i]
            # Remove first column if data contains only letters
            if i != 0 or not search.match(data[i]):
                # Remove characters that cause issues (%/)
                badchars=['%','/']
                columns[i] = ''.join(j for j in columns[i] if j not in badchars)
                string = "%s=%s" %(columns[i].strip('%/'), data[i].strip())
		### debug
		#print string
                self.stats.append(string)
		### debug
                #print "Appended data: ", data[i]

def CheckBin(program):
    '''Ensure the program exists in the PATH'''
    for path in os.environ.get('PATH', '').split(':'):
        if os.path.exists(os.path.join(path, program)) and \
           not os.path.isdir(os.path.join(path, program)):
               return os.path.join(path, program)
               #return True
    return False


def Main(args):
    # Ensure a profile (aka myOpts) is selected
    if not len(args) > 1:
        print 'ERROR: no profile selected'
        return(ERR_UNKN)
    if not CheckBin('sar'):
        print 'ERROR: sar not found on PATH (%s), install sysstat' %os.environ['PATH']
        return(ERR_CRIT)

    # Profiles may need to be modified for different versions of the sysstat package
    # This would be a good candidate for a config file
    myOpts = {}
    myOpts['pagestat'] = 'sar -B 1 1'
    myOpts['cpu'] = 'sar 1 1'
    myOpts['memory_util'] = 'sar -r 1 1'
    myOpts['memory_stat'] = 'sar -R 1 1'
    myOpts['io_transfer'] = 'sar -b 1 1'
    myOpts['queueln_load'] = 'sar -q 1 1'
    myOpts['swap_util'] = 'sar -S 1 1'
    myOpts['swap_stat'] = 'sar -W 1 1'
    myOpts['task'] = 'sar -w 1 1'
    myOpts['kernel'] = 'sar -v 1 1'
    myOpts['disk'] = 'sar -d -p 1 1'

    # If profile uses combined output you must pick one device to report on ie sda for disk
    if args[1] in myOpts:
        if args[1] == 'disk':
            if len(args) > 2:
                sar = SarNRPE(myOpts[args[1]],args[2])
            else:
                print 'ERROR: no device specified'
                return(ERR_UNKN)
        else:
            sar = SarNRPE(myOpts[args[1]])
    else:
        print 'ERROR: option not defined'
        return(ERR_UNKN)

    # Output in NRPE format
    print 'sar OK |', ' '.join(sar.stats)

    return(ERR_OK)

if __name__ == '__main__':
    try:
        result = Main(sys.argv)
    except:
        print sys.exc_info()
        print 'Unexpected Error'
        exit(3)
    sys.exit(result)
