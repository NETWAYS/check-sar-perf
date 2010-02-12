#!/usr/bin/env python
import os
import sys
from subprocess import *


os.environ['PATH'] = '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/bin'

class SarNRPE:

    '''Call sar and parse statistics returning in NRPE format'''
    def __init__(self, command, handler):
        sar=Popen(command, shell=True, stdout=PIPE, stderr=PIPE)
        (sout,serr) = sar.communicate()
        parser = getattr(self, handler)
        if callable(parser):
            parser(sout)
        else:
            print 'ERROR: parser does not exist'
            sys.exit(1)

    def standard(self, sout):
        '''Standard parser for non multi-device output'''
        self.Average = sout.split('\n')[-2].split()
        # remove 'Average:'
        self.Average.pop(0)
        self.Columns = sout.split('\n')[-4].split()
        # Remove Timestamp
        self.Columns.pop(0)
        self.Columns.pop(0)
        self.stats = []
        # Create dictionary
        for i in range(len(self.Columns)):
            string = "'%s'=%s" %(self.Columns[i], self.Average[i])
            self.stats.append(string)

def CheckBin(program):
    for path in os.environ.get('PATH', '').split(':'):
        if os.path.exists(os.path.join(path, program)) and \
           not os.path.isdir(os.path.join(path, program)):
               return os.path.join(path, program)
               #return True
    return False


def Main(args):
    if not CheckBin('sar'):
        print 'ERROR: sar not found on PATH (%s), install sysstat' %os.environ['PATH']
        sys.exit(1)
    myOpts = {}
    myOpts['paging'] = 'sar -B 1 1'
    myOpts['cpu'] = 'sar -C 1 1'
    myOpts['memory_util'] = 'sar -r 1 1'
    myOpts['memory_stat'] = 'sar -R 1 1'
    myOpts['io_transfer'] = 'sar -b 1 1'
    myOpts['queueln_load'] = 'sar -q 1 1'
    myOpts['swap_util'] = 'sar -S 1 1'
    myOpts['swap_stat'] = 'sar -W 1 1'
    myOpts['kernel'] = 'sar -v 1 1'

    if args[1] in myOpts:
        sar = SarNRPE(myOpts[args[1]],'standard')
    else:
        print 'ERROR: option not defined'
        sys.exit(1)
    # Output in NRPE format
    print '|', ' '.join(sar.stats)

if __name__ == '__main__':
    Main(sys.argv)