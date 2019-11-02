#!/usr/bin/env python3
"""UPSmodule  -  utility for interacting with APC UPS

    Copyright (C) 2019  RueiKe

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
__author__ = "RueiKe"
__copyright__ = "Copyright (C) 2019 RueiKe"
__credits__ = []
__license__ = "GNU General Public License"
__program_name__ = "ups-utils"
__version__ = "v0.0.1"
__maintainer__ = "RueiKe"
__status__ = "Development"

import os
import sys
import re
import shutil
import shlex
import subprocess
try:
    from config import (ups_IP, ups_type, snmp_community, suspend_threshold, read_interval,
                        suspend_script, resume_script, shutdown_script)
except ModuleNotFoundError:
    print('The config.py file is missing.  Use config.py.template as a template.')
    print('Use chmod 600 on config.py to protect sensitive information.')
    sys.exit(-1)


class ApcUpsSnmp:
    def __init__(self):
        DEFAULT_READ_INTERVAL = 30
        READ_INTERVAL_LIMIT = 10
        DEFAULT_SUSPEND_THRESHOLD = 5
        SUSPEND_THRESHOLD_LIMIT = 2

        self.all_mib_cmds = {'apc': {'mib_ups_info': {'iso': 'iso.3.6.1.2.1.1.1.0',
                                                      'name': 'General UPS Information',
                                                      'decode': None},
                                     'mib_bios_serial_number': {'iso': 'iso.3.6.1.4.1.318.1.1.1.1.2.3.0',
                                                                'name': 'UPS BIOS Serial Number',
                                                                'decode': None},
                                     'mib_firmware_revision': {'iso': 'iso.3.6.1.4.1.318.1.1.1.1.2.1.0',
                                                               'name': 'UPS Firmware Revision',
                                                               'decode': None},
                                     'mib_ups_type': {'iso': 'iso.3.6.1.4.1.318.1.1.1.1.1.1.0',
                                                      'name': 'UPS Type',
                                                      'decode': None},
                                     'mib_ups_contact': {'iso': 'iso.3.6.1.2.1.1.4.0',
                                                         'name': 'UPS Contact',
                                                         'decode': None},
                                     'mib_ups_location': {'iso': 'iso.3.6.1.2.1.1.6.0',
                                                          'name': 'UPS Location',
                                                          'decode': None},
                                     'mib_ups_manufacture_data': {'iso': 'iso.3.6.1.4.1.318.1.1.1.1.2.2.0',
                                                                  'name': 'UPS Manufacture Date',
                                                                  'decode': None},
                                     'mib_ups_name': {'iso': 'iso.3.6.1.2.1.33.1.1.5.0',
                                                      'name': 'UPS Name',
                                                      'decode': None},
                                     'mib_battery_capacity': {'iso': 'iso.3.6.1.4.1.318.1.1.1.2.2.1.0',
                                                              'name': 'Percentage of Total Capacity',
                                                              'decode': None},
                                     'mib_battery_temperature': {'iso': 'iso.3.6.1.4.1.318.1.1.1.2.2.2.0',
                                                                 'name': 'Battery Temperature in C',
                                                                 'decode': None},
                                     'mib_battery_status': {'iso': 'iso.3.6.1.4.1.318.1.1.1.2.1.1.0',
                                                            'name': 'Battery Status',
                                                            'decode': {'1': 'Unknown',
                                                                       '2': 'Battery Normal',
                                                                       '3': 'Battery Low',
                                                                       '4': 'Battery in Fault Condition'}},
                                     'mib_time_on_battery': {'iso': 'iso.3.6.1.4.1.318.1.1.1.2.1.2.0',
                                                             'name': 'Time on Battery',
                                                             'decode': None},
                                     'mib_battery_runtime_remain': {'iso': 'iso.3.6.1.4.1.318.1.1.1.2.2.3.0',
                                                                    'name': 'Runtime Remaining',
                                                                    'decode': None},
                                     'mib_battery_replace ': {'iso': 'iso.3.6.1.4.1.318.1.1.1.2.2.4.0',
                                                              'name': 'Battery replacement',
                                                              'decode': {'1': 'OK',
                                                                         '2': 'Replacement Required'}},
                                     'mib_input_voltage': {'iso': 'iso.3.6.1.4.1.318.1.1.1.3.2.1.0',
                                                           'name': 'Input Voltage',
                                                           'decode': None},
                                     'mib_input_frequency': {'iso': 'iso.3.6.1.4.1.318.1.1.1.3.2.4.0',
                                                             'name': 'Input Frequency Hz',
                                                             'decode': None},
                                     'mib_reason_for_last_transfer': {'iso': 'iso.3.6.1.4.1.318.1.1.1.3.2.5.0',
                                                                      'name': 'Last Transfer Event',
                                                                      'decode': {'1': 'No Transfer',
                                                                                 '2': 'High Line Voltage',
                                                                                 '3': 'Brownout',
                                                                                 '4': 'Loss of Main Power',
                                                                                 '5': 'Small Temp Power Drop',
                                                                                 '6': 'Large Temp Power Drop',
                                                                                 '7': 'Small Spike',
                                                                                 '8': 'Large Spike',
                                                                                 '9': 'UPS Self Test',
                                                                                 '10': 'Excessive Input V Fluctuation'}},
                                     'mib_output_voltage': {'iso': 'iso.3.6.1.4.1.318.1.1.1.4.2.1.0',
                                                            'name': 'Output Voltage',
                                                            'decode': None},
                                     'mib_output_frequency': {'iso': 'iso.3.6.1.4.1.318.1.1.1.4.2.2.0',
                                                              'name': 'Output Frequency Hz',
                                                              'decode': None},
                                     'mib_output_load': {'iso': 'iso.3.6.1.4.1.318.1.1.1.4.2.3.0',
                                                         'name': 'Output load as % of capacity',
                                                         'decode': None},
                                     'mib_output_current': {'iso': 'iso.3.6.1.4.1.318.1.1.1.4.2.4.0',
                                                            'name': 'Output current in Amps',
                                                            'decode': None},
                                     'mib_comms': {'iso': 'iso.3.6.1.4.1.318.1.1.1.8.1.0',
                                                   'name': 'Communicating with UPS Device',
                                                   'decode': {'1': 'Communication OK',
                                                              '2': 'Communication Error'}},
                                     'mib_last_self_test_result': {'iso': 'iso.3.6.1.4.1.318.1.1.1.7.2.3.0',
                                                                   'name': 'Last Self Test Results',
                                                                   'decode': {'1': 'OK',
                                                                              '2': 'Failed',
                                                                              '3': 'Invalid',
                                                                              '4': 'In Progress'}},
                                     'mib_last_self_test_date': {'iso': 'iso.3.6.1.4.1.318.1.1.1.7.2.4.0',
                                                                 'name': 'Date of Last Self Test',
                                                                 'decode': None}},
                             'eaton': {'mib_ups_info': {'iso': 'iso.3.6.1.2.1.1.1.0',
                                                        'name': 'General UPS Information',
                                                        'decode': None},
                                       'mib_bios_serial_number': {'iso': 'iso.3.6.1.4.1.318.1.1.1.1.2.3.0',
                                                                  'name': 'UPS BIOS Serial Number',
                                                                  'decode': None},
                                       'mib_firmware_revision': {'iso': 'iso.3.6.1.4.1.318.1.1.1.1.2.1.0',
                                                                 'name': 'UPS Firmware Revision',
                                                                 'decode': None},
                                       'mib_ups_type': {'iso': 'iso.3.6.1.4.1.318.1.1.1.1.1.1.0',
                                                        'name': 'UPS Type',
                                                        'decode': None},
                                       'mib_ups_contact': {'iso': 'iso.3.6.1.2.1.1.4.0',
                                                           'name': 'UPS Contact',
                                                           'decode': None},
                                       'mib_ups_location': {'iso': 'iso.3.6.1.2.1.1.6.0',
                                                            'name': 'UPS Location',
                                                            'decode': None},
                                       'mib_ups_manufacture_data': {'iso': 'iso.3.6.1.4.1.318.1.1.1.1.2.2.0',
                                                                    'name': 'UPS Manufacture Date',
                                                                    'decode': None},
                                       'mib_ups_name': {'iso': 'iso.3.6.1.2.1.33.1.1.5.0',
                                                        'name': 'UPS Name',
                                                        'decode': None},
                                       'mib_battery_capacity': {'iso': 'iso.3.6.1.4.1.318.1.1.1.2.2.1.0',
                                                                'name': 'Percentage of Total Capacity',
                                                                'decode': None},
                                       'mib_battery_temperature': {'iso': 'iso.3.6.1.4.1.318.1.1.1.2.2.2.0',
                                                                   'name': 'Battery Temperature in C',
                                                                   'decode': None},
                                       'mib_battery_status': {'iso': 'iso.3.6.1.4.1.318.1.1.1.2.1.1.0',
                                                              'name': 'Battery Status',
                                                              'decode': {'1': 'Unknown',
                                                                         '2': 'Battery Normal',
                                                                         '3': 'Battery Low',
                                                                         '4': 'Battery in Fault Condition'}},
                                       'mib_time_on_battery': {'iso': 'iso.3.6.1.4.1.318.1.1.1.2.1.2.0',
                                                               'name': 'Time on Battery',
                                                               'decode': None},
                                       'mib_battery_runtime_remain': {'iso': 'iso.3.6.1.4.1.318.1.1.1.2.2.3.0',
                                                                      'name': 'Runtime Remaining',
                                                                      'decode': None},
                                       'mib_battery_replace ': {'iso': 'iso.3.6.1.4.1.318.1.1.1.2.2.4.0',
                                                                'name': 'Battery replacement',
                                                                'decode': {'1': 'OK',
                                                                           '2': 'Replacement Required'}},
                                       'mib_input_voltage': {'iso': 'iso.3.6.1.4.1.318.1.1.1.3.2.1.0',
                                                             'name': 'Input Voltage',
                                                             'decode': None},
                                       'mib_input_frequency': {'iso': 'iso.3.6.1.4.1.318.1.1.1.3.2.4.0',
                                                               'name': 'Input Frequency Hz',
                                                               'decode': None},
                                       'mib_reason_for_last_transfer': {'iso': 'iso.3.6.1.4.1.318.1.1.1.3.2.5.0',
                                                                        'name': 'Last Transfer Event',
                                                                        'decode': {'1': 'No Transfer',
                                                                                   '2': 'High Line Voltage',
                                                                                   '3': 'Brownout',
                                                                                   '4': 'Loss of Main Power',
                                                                                   '5': 'Small Temp Power Drop',
                                                                                   '6': 'Large Temp Power Drop',
                                                                                   '7': 'Small Spike',
                                                                                   '8': 'Large Spike',
                                                                                   '9': 'UPS Self Test',
                                                                                   '10': 'Excessive Input V Fluctuation'}},
                                       'mib_output_voltage': {'iso': 'iso.3.6.1.4.1.318.1.1.1.4.2.1.0',
                                                              'name': 'Output Voltage',
                                                              'decode': None},
                                       'mib_output_frequency': {'iso': 'iso.3.6.1.4.1.318.1.1.1.4.2.2.0',
                                                                'name': 'Output Frequency Hz',
                                                                'decode': None},
                                       'mib_output_load': {'iso': 'iso.3.6.1.4.1.318.1.1.1.4.2.3.0',
                                                           'name': 'Output load as % of capacity',
                                                           'decode': None},
                                       'mib_output_current': {'iso': 'iso.3.6.1.4.1.318.1.1.1.4.2.4.0',
                                                              'name': 'Output current in Amps',
                                                              'decode': None},
                                       'mib_comms': {'iso': 'iso.3.6.1.4.1.318.1.1.1.8.1.0',
                                                     'name': 'Communicating with UPS Device',
                                                     'decode': {'1': 'Communication OK',
                                                                '2': 'Communication Error'}},
                                       'mib_last_self_test_result': {'iso': 'iso.3.6.1.4.1.318.1.1.1.7.2.3.0',
                                                                     'name': 'Last Self Test Results',
                                                                     'decode': {'1': 'OK',
                                                                                '2': 'Failed',
                                                                                '3': 'Invalid',
                                                                                '4': 'In Progress'}},
                                       'mib_last_self_test_date': {'iso': 'iso.3.6.1.4.1.318.1.1.1.7.2.4.0',
                                                                   'name': 'Date of Last Self Test',
                                                                   'decode': None}}}

        if ups_type not in self.all_mib_cmds.keys():
            print('Invalid UPS type: {}, Valid entries: '.format(ups_type),  list(self.all_mib_cmds.keys()))
            sys.exit(-1)

        self.ups_type = ups_type
        self.mib_commands = self.all_mib_cmds[ups_type]

        if not shutil.which('snmpget'):
            print('Missing dependency: sudo apt install snmp')
            sys.exit(-1)

        self.suspend_script = suspend_script
        if suspend_script:
            if not os.path.isfile(self.suspend_script):
                print('Missing suspend script: {}'.format(self.suspend_script))
                sys.exit(-1)
            print('Suspend script: {}'.format(self.suspend_script))

        self.resume_script = resume_script
        if resume_script:
            if not os.path.isfile(self.resume_script):
                print('Missing resume script: {}'.format(self.resume_script))
                sys.exit(-1)
            print('Resume script: {}'.format(self.resume_script))

        self.shutdown_script = shutdown_script
        if shutdown_script:
            if not os.path.isfile(self.shutdown_script):
                print('Missing shutdown script: {}'.format(self.shutdown_script))
                sys.exit(-1)
            print('Shutdown script: {}'.format(self.shutdown_script))

        self.read_interval = DEFAULT_READ_INTERVAL
        if isinstance(read_interval, int):
            if read_interval > READ_INTERVAL_LIMIT:
                self.read_interval = read_interval
            else:
                print('Invalid read interval in config.py.  Using default.')
        print('Read Interval: {}'.format(self.read_interval))

        self.suspend_threshold = DEFAULT_SUSPEND_THRESHOLD
        if isinstance(suspend_threshold, int):
            if suspend_threshold > SUSPEND_THRESHOLD_LIMIT:
                self.suspend_threshold = suspend_threshold
            else:
                print('Invalid suspend threshold in config.py.  Using default.')
        print('Suspend Threshold: {}'.format(self.suspend_threshold))

    def shutdown(self):
        if not self.shutdown_script:
            print('No shutdown script defined')
            return
        try:
            cmd = subprocess.Popen(shlex.split(self.shutdown_script), shell=False, stdout=subprocess.PIPE)
            while True:
                if cmd.poll() is not None:
                    break
                time.sleep(1)
        except:
            print("Error: could not execute shutdown script: %s" % shutdown_script, file=sys.stderr)

    def resume(self):
        if not self.resume_script:
            print('No resume script defined')
            return
        try:
            cmd = subprocess.Popen(shlex.split(self.resume_script), shell=False, stdout=subprocess.PIPE)
            while True:
                if cmd.poll() is not None:
                    break
                time.sleep(1)
        except:
            print("Error: could not execute resume script: %s" % resume_script, file=sys.stderr)

    def suspend(self):
        if not self.suspend_script:
            print('No suspend script defined')
            return
        try:
            cmd = subprocess.Popen(shlex.split(self.suspend_script), shell=False, stdout=subprocess.PIPE)
            while True:
                if cmd.poll() is not None:
                    break
                time.sleep(1)
        except:
            print("Error: could not execute suspend script: %s" % suspend_script, file=sys.stderr)

    def send_snmp_command(self, command_name, display=False):
        cmd_mib = self.mib_commands[command_name]['iso']
        cmd_str = 'snmpget -v2c -c {} {} {}'.format(snmp_community, ups_IP, cmd_mib)
        snmp_output = subprocess.check_output(shlex.split(cmd_str),
                                              shell=False,
                                              stderr=subprocess.DEVNULL).decode().split('\n')
        value = ''
        value_minute = -1
        value_str = 'UNK'
        for line in snmp_output:
            if re.match(r'.*=.*:.*', line):
                value = line.split(':', 1)[1]
                value = re.sub(r'\"', '', value).strip()
        if self.mib_commands[command_name]['decode']:
            if value in self.mib_commands[command_name]['decode'].keys():
                value = self.mib_commands[command_name]['decode'][value]
        if display:
            print('{}: {}'.format(self.mib_commands[command_name]['name'], value))
        if command_name == 'mib_time_on_battery' or command_name == 'mib_battery_runtime_remain':
            # Create a minute, string tuple
            value_items = re.sub(r'\(', '', value).split(')')
            if len(value_items) >= 2:
                value_minute, value_str = value_items
            value = (int(value_minute)/60/60, value_str)
        return value

    def list_snmp_commands(self):
        for k, v in self.mib_commands.items():
            print('{}: Value: {}'.format(k, v['iso']))
            print('    Description: {}'.format(v['name']))
            if v['decode']:
                for k2, v2 in v['decode'].items():
                    print('        {}: {}'.format(k2, v2))


def about():
    # About me
    print(__doc__)
    print("Author: ", __author__)
    print("Copyright: ", __copyright__)
    print("Credits: ", __credits__)
    print("License: ", __license__)
    print("Version: ", __version__)
    print("Maintainer: ", __maintainer__)
    print("Status: ", __status__)
    sys.exit(0)


if __name__ == "__main__":
    about()
