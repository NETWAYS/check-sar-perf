#!/usr/bin/env python3

import unittest
import unittest.mock as mock
import sys

sys.path.append('..')

from check_sar_perf import check_bin
from check_sar_perf import commandline
from check_sar_perf import sort_output,sort_combined_output
from check_sar_perf import SarNRPE
from check_sar_perf import main

fixture_sar_cpu = """
Linux 1.2.3-45-generic (unittest)       10/10/2010      _x86_64_	(1 CPU)

06:35:24        CPU     %user     %nice   %system   %iowait    %steal     %idle
06:35:25        all      0.00      0.00      0.00      0.00      0.00    100.00
Average:        all      0.00      0.00      0.00      0.00      0.00    100.00
"""

fixture_sar_disk = """
Linux 1.2.3-45-generic (unittest)       10/10/2010      _x86_64_	(1 CPU)

07:32:19    DEV       tps     rkB/s     wkB/s   areq-sz    aqu-sz     await     svctm     %util
07:32:20    sda      0.00      0.00      0.00      0.00      0.00      0.00      0.00      0.00
07:32:20    root      0.00      0.00      0.00      0.00      0.00      0.00      0.00      0.00
07:32:20    swap      0.00      0.00      0.00      0.00      0.00      0.00      0.00      0.00

Average:    DEV       tps     rkB/s     wkB/s   areq-sz    aqu-sz     await     svctm     %util
Average:    sda      0.00      0.00      0.00      0.00      0.00      0.00      0.00      0.00
Average:    root      0.00      0.00      0.00      0.00      0.00      0.00      0.00      0.00
Average:    swap      0.00      0.00      0.00      0.00      0.00      0.00      0.00      0.00
"""

fixture_sar_disk_sar12 = """
Linux 5.10.0-20-amd64 (debian)        04/14/23        _x86_64_	(2 CPU)

11:04:30          tps     rkB/s     wkB/s     dkB/s   areq-sz    aqu-sz     await     %util DEV
11:04:31         1.00      0.00      4.00      0.00      4.00      0.00      0.00      0.40 sda
Average:         1.00      0.00      4.00      0.00      4.00      0.00      0.00      0.40 sda
"""

class SarPerfTest(unittest.TestCase):

    def test_commandline(self):
        args = ['cpu']
        actual = commandline(args)
        self.assertEqual(actual.profile, ['cpu'])

        args = ['disk', '--device', 'foo']
        actual = commandline(args)
        self.assertEqual(actual.profile, ['disk'])

    def test_check_bin(self):
        actual = check_bin("foobar")
        self.assertFalse(actual)

        actual = check_bin("python")
        self.assertTrue(actual)

    def test_sort_output(self):
        expected = (['CPU', '%user', '%nice', '%system', '%iowait', '%steal', '%idle'], ['all', '0.00', '0.00', '0.00', '0.00', '0.00', '100.00'])
        actual = sort_output(fixture_sar_cpu)
        self.assertEqual(actual, expected)

    def test_sort_output_error_handling(self):
        expected = ([], [])
        actual = sort_output("foo")
        self.assertEqual(actual, expected)

    def test_sort_combined_output(self):

        expected = (['DEV', 'tps', 'rkB/s', 'wkB/s', 'areq-sz', 'aqu-sz', 'await', 'svctm', '%util'],
                    ['sda', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00', '0.00'])

        actual = sort_combined_output(fixture_sar_disk, 'sda')
        self.assertEqual(actual, expected)

    def test_sort_combined_output_sar12(self):

        expected = (['tps', 'rkB/s', 'wkB/s', 'dkB/s', 'areq-sz', 'aqu-sz', 'await', '%util', 'DEV'],
                    ['1.00', '0.00', '4.00', '0.00', '4.00', '0.00', '0.00', '0.40', 'sda'])

        actual = sort_combined_output(fixture_sar_disk_sar12, 'sda')
        self.assertEqual(actual, expected)

    def test_sort_combined_output_missing_dev(self):

        expected = (['DEV', 'tps', 'rkB/s', 'wkB/s', 'areq-sz', 'aqu-sz', 'await', 'svctm', '%util'],
                    [])

        actual = sort_combined_output(fixture_sar_disk, 'sdb')
        self.assertEqual(actual, expected)

class SarNRPETest(unittest.TestCase):

    @mock.patch('check_sar_perf.subprocess.Popen')
    def test_init(self, mock_popen):

        # Prepare mocked subprocess object
        m = mock.Mock()
        m.communicate.return_value=(fixture_sar_cpu.encode(), b'error')
        mock_popen.return_value.__enter__.return_value = m

        # Get actual data from Object
        s = SarNRPE("unittest")
        actual = s.stats

        expected = ['user=0.00', 'nice=0.00', 'system=0.00', 'iowait=0.00', 'steal=0.00', 'idle=100.00']

        self.assertEqual(actual, expected)

    @mock.patch('check_sar_perf.subprocess.Popen')
    def test_disk(self, mock_popen):

        # Prepare mocked subprocess object
        m = mock.Mock()
        m.communicate.return_value=(fixture_sar_disk.encode(), b'error')
        mock_popen.return_value.__enter__.return_value = m

        # Get actual data from Object
        s = SarNRPE("unittest")
        actual = s.stats

        expected = ['tps=0.00', 'rkBs=0.00', 'wkBs=0.00', 'areq-sz=0.00', 'aqu-sz=0.00', 'await=0.00', 'svctm=0.00', 'util=0.00']

        self.assertEqual(actual, expected)

class MainTest(unittest.TestCase):

    @mock.patch('builtins.print')
    @mock.patch('check_sar_perf.check_bin')
    def test_main_no_sar(self, mock_bin, mock_print):
        mock_bin.return_value = False
        args = commandline(['cpu'])
        actual = main(args)

        expected = 2
        self.assertEqual(actual, expected)

    @mock.patch('builtins.print')
    @mock.patch('check_sar_perf.SarNRPE', side_effect=KeyError('BOOM!'))
    @mock.patch('check_sar_perf.check_bin')
    def test_main_sar_error(self, mock_bin, mock_sar, mock_print):
        mock_bin.return_value = True

        args = commandline(['cpu'])
        actual = main(args)
        expected = 3
        self.assertEqual(actual, expected)

        args = commandline(['disk', '-d', 'unittest'])
        actual = main(args)
        expected = 3
        self.assertEqual(actual, expected)

        args = commandline(['custom', '-c', 'sar 1 1'])
        actual = main(args)
        expected = 3
        self.assertEqual(actual, expected)

    @mock.patch('builtins.print')
    @mock.patch('check_sar_perf.SarNRPE')
    @mock.patch('check_sar_perf.check_bin')
    def test_main_sar_ok(self, mock_bin, mock_sar, mock_print):
        mock_bin.return_value = True
        mock_sar.stats = ['test']

        args = commandline(['cpu'])
        actual = main(args)
        expected = 0
        self.assertEqual(actual, expected)

        mock_print.assert_called_once_with('OK: sar |', '')

if __name__ == '__main__':
    unittest.main()
