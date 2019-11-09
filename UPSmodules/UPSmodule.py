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
import shlex
import time
import datetime
import json
import subprocess
try:
    from UPSmodules import env
except ModuleNotFoundError:
    import env
try:
    from config import (suspend_threshold, read_interval,
                        suspend_script, resume_script, shutdown_script,
                        shutdown_capacity_threshold, shutdown_time_remaining_threshold)
except ModuleNotFoundError:
    print('The config.py file is missing.  Use config.py.template as a template.')
    print('Use chmod 600 on config.py to protect sensitive information.')
    sys.exit(-1)


class UPSsnmp:
    def __init__(self):
        # UPS list from config.json for monitor and ls utils.
        self.ups_list = {}
        self.active_ups = {}

        # UPS from config.py for ups-daemon utility.
        self.daemon_params = {'suspend_script': '', 'resume_script': '', 'shutdown_script': '',
                              'suspend_threshold': env.ut_const.DEFAULT_SUSPEND_THRESHOLD,
                              'read_interval': env.ut_const.DEFAULT_READ_INTERVAL,
                              'shutdown_capacity_threshold': env.ut_const.BATTERY_CAPACITY_SHUTDOWN_THRESHOLD,
                              'shutdown_time_remaining_threshold': env.ut_const.BATTERY_TIME_REMAINING_SHUTDOWN_THRESHOLD}

        self.monitor_mib_cmds = {'static': ['mib_ups_name', 'mib_ups_info', 'mib_bios_serial_number',
                                            'mib_firmware_revision', 'mib_ups_type', 'mib_ups_location',
                                            'mib_ups_manufacture_date', 'mib_ups_contact'],
                                 'dynamic': ['mib_battery_capacity', 'mib_battery_status', 'mib_time_on_battery',
                                             'mib_battery_runtime_remain', 'mib_input_voltage', 'mib_input_frequency',
                                             'mib_output_voltage', 'mib_output_frequency', 'mib_output_load',
                                             'mib_output_current', 'mib_output_power']}
        self.output_mib_cmds = ['mib_output_voltage', 'mib_output_frequency', 'mib_output_load', 'mib_output_current',
                                'mib_output_power']
        self.input_mib_cmds = ['mib_input_voltage', 'mib_input_frequency']

        self.all_mib_cmds = {
                      # MiBs for APC UPS with AP9630 NMC
                      'apc-ap9630': {'mib_ups_info': {'iso': 'iso.3.6.1.2.1.1.1.0',
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
                                     'mib_ups_model': {'iso': 'iso.3.6.1.4.1.318.1.1.1.1.2.5.0',
                                                       'name': 'UPS Model Number',
                                                       'decode': None},
                                     'mib_ups_contact': {'iso': 'iso.3.6.1.2.1.1.4.0',
                                                         'name': 'UPS Contact',
                                                         'decode': None},
                                     'mib_ups_location': {'iso': 'iso.3.6.1.2.1.1.6.0',
                                                          'name': 'UPS Location',
                                                          'decode': None},
                                     'mib_ups_manufacture_date': {'iso': 'iso.3.6.1.4.1.318.1.1.1.1.2.2.0',
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
                                     'mib_output_power': {'iso': 'iso.3.6.1.4.1.318.1.1.1.4.2.8.0',
                                                          'name': 'Output power in W',
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
                      # MiBs for Eaton UPS with PowerWalker NMC
                      'eaton-pw': {'mib_ups_info': {'iso': 'iso.3.6.1.2.1.1.1.0',
                                                    'name': 'General UPS Information',
                                                    'decode': None},
                                   'mib_ups_manufacturer': {'iso': 'iso.3.6.1.4.1.935.10.1.1.1.1.0',
                                                            'name': 'UPS Manufacturer',
                                                            'decode': None},
                                   #'mib_bios_serial_number': {'iso': 'iso.3.6.1.4.1.935.10.1.1.1.4.0',
                                                              #'name': 'UPS BIOS Serial Number',
                                                              #'decode': None},
                                   'mib_firmware_revision': {'iso': 'iso.3.6.1.4.1.935.10.1.1.1.6.0',
                                                             'name': 'UPS Firmware Revision',
                                                             'decode': None},
                                   'mib_ups_type': {'iso': 'iso.3.6.1.4.1.935.10.1.1.1.2.0',
                                                    'name': 'UPS Type',
                                                    'decode': None},
                                   'mib_ups_contact': {'iso': 'iso.3.6.1.2.1.1.4.0',
                                                       'name': 'UPS Contact',
                                                       'decode': None},
                                   'mib_ups_location': {'iso': 'iso.3.6.1.2.1.1.6.0',
                                                        'name': 'UPS Location',
                                                        'decode': None},
                                   'mib_ups_manufacture_date': {'iso': 'iso.3.6.1.4.1.318.1.1.1.1.2.2.0',
                                                                'name': 'UPS Manufacture Date',
                                                                'decode': None},
                                   'mib_ups_name': {'iso': 'iso.3.6.1.2.1.33.1.1.5.0',
                                                    'name': 'UPS Name',
                                                    'decode': None},
                                   'mib_battery_capacity': {'iso': 'iso.3.6.1.4.1.935.10.1.1.3.4.0',
                                                            'name': 'Percentage of Total Capacity',
                                                            'decode': None},
                                   'mib_system_temperature': {'iso': 'iso.3.6.1.4.1.935.10.1.1.2.2.0',
                                                              'name': 'System Temperature in C',
                                                              'decode': None},
                                   'mib_system_uptime': {'iso': 'iso.3.6.1.2.1.1.3.0',
                                                         'name': 'System Uptime',
                                                         'decode': None},
                                   'mib_system_status': {'iso': 'iso.3.6.1.4.1.935.10.1.1.3.1.0',
                                                         'name': 'UPS System Status',
                                                         'decode': {'1': 'Power On',
                                                                    '2': 'Standby',
                                                                    '3': 'Bypass',
                                                                    '4': 'Line',
                                                                    '5': 'Battery',
                                                                    '6': 'Battery Test',
                                                                    '7': 'Fault',
                                                                    '8': 'Converter',
                                                                    '9': 'ECO',
                                                                    '10': 'Shutdown',
                                                                    '11': 'On Booster',
                                                                    '12': 'On Reducer',
                                                                    '13': 'Other'}},
                                   'mib_battery_status': {'iso': 'iso.3.6.1.4.1.935.10.1.1.3.1.0',
                                                          'name': 'Battery Status',
                                                          'decode': {'1': 'Unknown',
                                                                     '2': 'Battery Normal',
                                                                     '3': 'Battery Low',
                                                                     '4': 'Battery Depleted',
                                                                     '5': 'Battery Discharging',
                                                                     '6': 'Battery Failure'}},
                                   'mib_time_on_battery': {'iso': 'iso.3.6.1.4.1.935.10.1.1.3.2.0',
                                                           'name': 'Time on Battery',
                                                           'decode': None},
                                   'mib_battery_runtime_remain': {'iso': 'iso.3.6.1.4.1.935.10.1.1.3.3.0',
                                                                  'name': 'Runtime Remaining',
                                                                  'decode': None},
                                   #'mib_battery_replace ': {'iso': 'iso.3.6.1.4.1.318.1.1.1.2.2.4.0',
                                                            #'name': 'Battery replacement',
                                                            #'decode': {'1': 'OK',
                                                                       #'2': 'Replacement Required'}},
                                   'mib_input_voltage': {'iso': 'iso.3.6.1.4.1.935.10.1.1.2.16.1.3.1',
                                                         'name': 'Input Voltage V',
                                                         'decode': None},
                                   'mib_input_frequency': {'iso': 'iso.3.6.1.4.1.935.10.1.1.2.16.1.2.1',
                                                           'name': 'Input Frequency Hz',
                                                           'decode': None},
                                   # TODO is there an Eaton equivalent
                                   #'mib_reason_for_last_transfer': {'iso': 'iso.3.6.1.4.1.318.1.1.1.3.2.5.0',
                                                                    #'name': 'Last Transfer Event',
                                                                    #'decode': {'1': 'No Transfer',
                                                                               #'2': 'High Line Voltage',
                                                                               #'3': 'Brownout',
                                                                               #'4': 'Loss of Main Power',
                                                                               #'5': 'Small Temp Power Drop',
                                                                               #'6': 'Large Temp Power Drop',
                                                                               #'7': 'Small Spike',
                                                                               #'8': 'Large Spike',
                                                                               #'9': 'UPS Self Test',
                                                                               #'10': 'Excessive Input V Fluctuation'}},
                                   'mib_output_voltage': {'iso': 'iso.3.6.1.4.1.935.10.1.1.2.18.1.3.1',
                                                          'name': 'Output Voltage',
                                                          'decode': None},
                                   'mib_output_frequency': {'iso': 'iso.3.6.1.4.1.935.10.1.1.2.18.1.2.1',
                                                            'name': 'Output Frequency Hz',
                                                            'decode': None},
                                   'mib_output_load': {'iso': 'iso.3.6.1.4.1.935.10.1.1.2.18.1.7.1',
                                                       'name': 'Output load as % of capacity',
                                                       'decode': None},
                                   'mib_output_current': {'iso': 'iso.3.6.1.4.1.935.10.1.1.2.18.1.4.1',
                                                          'name': 'Output current in Amps',
                                                          'decode': None},
                                   'mib_output_power': {'iso': 'iso.3.6.1.4.1.935.10.1.1.2.18.1.5.1',
                                                        'name': 'Output power in W',
                                                        'decode': None},
                                   'mib_last_self_test_result': {'iso': 'iso.3.6.1.4.1.935.10.1.1.7.3.0',
                                                                 'name': 'Last Self Test Results',
                                                                 'decode': {'1': 'Idle',
                                                                            '2': 'Processing',
                                                                            '3': 'No Failure',
                                                                            '4': 'Failure/Warning',
                                                                            '5': 'Not Possible',
                                                                            '6': 'Test Cancel'}},
                                   'mib_last_self_test_date': {'iso': 'iso.3.6.1.4.1.935.10.1.1.7.4.0',
                                                               'name': 'Date of Last Self Test',
                                                               'decode': None}}}
        # TODO add error checking here
        self.read_ups_list()
        self.check_ups_list()

    @staticmethod
    def mib_commands(ups_item):
        return ups_item['mib_commands']

    def get_monitor_mib_commands(self, type='dynamic'):
        return self.monitor_mib_cmds[type]

    def active_ups_mib_commands(self):
        return self.active_ups['mib_commands']

    def active_ups_name(self):
        return self.active_ups['display_name']

    def active_ups_ip(self):
        return self.active_ups['ups_IP']

    def set_active_ups(self, ups_item):
        self.active_ups = ups_item

    def check_ups_list(self):
        daemon_cnt = 0
        ups_cnt = 0
        for k, v in self.ups_list.items():
            if self.check_ups_type(v['ups_type']):
                ups_cnt += 1
                v['compatible'] = True
                v['mib_commands'] = self.all_mib_cmds[v['ups_type']]
                if v['daemon']:
                    daemon_cnt += 1
                    self.active_ups = v
            else:
                v['compatible'] = False
                v['mib_commands'] = None
        print('config.json contains {} total UPSs and {} daemon UPS'.format(ups_cnt, daemon_cnt))

    def set_daemon_ups(self):
        for k, v in self.ups_list.items():
            if v['daemon']:
                self.active_ups = v
                return True
        return False

    def set_daemon_parameters(self):
        self.daemon_params['suspend_script'] = suspend_script
        if suspend_script:
            if not os.path.isfile(suspend_script):
                print('Missing suspend script: {}'.format(suspend_script))
                sys.exit(-1)
            print('Suspend script: {}'.format(suspend_script))

        self.daemon_params['resume_script'] = resume_script
        if resume_script:
            if not os.path.isfile(resume_script):
                print('Missing resume script: {}'.format(resume_script))
                sys.exit(-1)
            print('Resume script: {}'.format(resume_script))

        self.daemon_params['shutdown_script'] = shutdown_script
        if shutdown_script:
            if not os.path.isfile(shutdown_script):
                print('Missing shutdown script: {}'.format(shutdown_script))
                sys.exit(-1)
            print('Shutdown script: {}'.format(shutdown_script))

        if isinstance(read_interval, int):
            if read_interval >= env.ut_const.READ_INTERVAL_LIMIT:
                self.daemon_params['read_interval'] = read_interval
            else:
                print('Invalid read interval in config.py.  Using default.')
        print('Read Interval: {} sec'.format(self.daemon_params['read_interval']))

        if isinstance(suspend_threshold, int):
            if suspend_threshold >= env.ut_const.SUSPEND_THRESHOLD_LIMIT:
                self.daemon_params['suspend_threshold'] = suspend_threshold
            else:
                print('Invalid suspend threshold in config.py.  Using default.')
        print('Suspend Threshold: {} min'.format(self.daemon_params['suspend_threshold']))

        if isinstance(shutdown_capacity_threshold, int):
            if shutdown_capacity_threshold >= env.ut_const.BATTERY_CAPACITY_SHUTDOWN_THRESHOLD:
                self.daemon_params['battery_capacity_shutdown_threshold'] = shutdown_capacity_threshold
            else:
                print('Invalid battery capacity shutdown threshold in config.py.  Using default.')
        print('Battery Capacity Shutdown Threshold: {}%'.format(self.daemon_params['battery_capacity_shutdown_threshold']))

        if isinstance(shutdown_time_remaining_threshold, int):
            if shutdown_time_remaining_threshold >= env.ut_const.BATTERY_TIME_REMAINING_SHUTDOWN_THRESHOLD:
                self.daemon_params['battery_time_remaining_shutdown_threshold'] = shutdown_time_remaining_threshold
            else:
                print('Invalid battery time remaining shutdown threshold in config.py.  Using default.')
        print('Battery time remaining Shutdown Threshold: {} min'.format(
               self.daemon_params['battery_time_remaining_shutdown_threshold']))

    def shutdown(self):
        if not self.daemon_params['shutdown_script']:
            print('No shutdown script defined')
            return
        try:
            cmd = subprocess.Popen(shlex.split(self.daemon_params['shutdown_script']),
                                   shell=False, stdout=subprocess.PIPE)
            while True:
                if cmd.poll() is not None:
                    break
                time.sleep(1)
        except:
            print('Error: could not execute shutdown script: {}'.format(self.daemon_params['shutdown_script']),
                  file=sys.stderr)

    def resume(self):
        if not self.daemon_params['resume_script']:
            print('No resume script defined')
            return
        try:
            cmd = subprocess.Popen(shlex.split(self.daemon_params['resume_script']),
                                   shell=False, stdout=subprocess.PIPE)
            while True:
                if cmd.poll() is not None:
                    break
                time.sleep(1)
        except:
            print('Error: could not execute resume script: {}'.format(self.daemon_params['resume_script']),
                  file=sys.stderr)

    def suspend(self):
        if not self.daemon_params['suspend_script']:
            print('No suspend script defined')
            return
        try:
            cmd = subprocess.Popen(shlex.split(self.daemon_params['suspend_script']),
                                   shell=False, stdout=subprocess.PIPE)
            while True:
                if cmd.poll() is not None:
                    break
                time.sleep(1)
        except:
            print('Error: could not execute suspend script: {}'.format(self.daemon_params['suspend_script']),
                  file=sys.stderr)

    def send_snmp_command(self, command_name, display=False):
        snmp_mib_commands = self.active_ups_mib_commands()
        cmd_mib = snmp_mib_commands[command_name]['iso']
        cmd_str = 'snmpget -v2c -c {} {} {}'.format(self.active_ups['snmp_community'],
                                                    self.active_ups['ups_IP'], cmd_mib)
        try:
            snmp_output = subprocess.check_output(shlex.split(cmd_str), shell=False,
                                                  stderr=subprocess.DEVNULL).decode().split('\n')
        except:
            print('Error executing snmp command to {} at {}.'.format(self.active_ups_name(), self.active_ups_ip()))
            return 'UPS Not Responding'

        value = ''
        value_minute = -1
        value_str = 'UNK'
        for line in snmp_output:
            # print('line:  {}'.format(line))
            if re.match(r'.*=.*:.*', line):
                value = line.split(':', 1)[1]
                value = re.sub(r'\"', '', value).strip()
        if snmp_mib_commands[command_name]['decode']:
            if value in snmp_mib_commands[command_name]['decode'].keys():
                value = snmp_mib_commands[command_name]['decode'][value]
        if self.active_ups['ups_type'] == 'eaton-pw':
            if command_name == 'mib_output_voltage' or command_name == 'mib_output_frequency':
                value = int(value) / 10.0
            elif command_name == 'mib_input_voltage' or command_name == 'mib_input_frequency':
                value = int(value) / 10.0
            elif command_name == 'mib_system_temperature':
                value = int(value) / 10.0
        if command_name == 'mib_time_on_battery' or command_name == 'mib_battery_runtime_remain':
            # Create a minute, string tuple
            if self.active_ups['ups_type'] == 'eaton-pw':
                # Process time for eaton-pw
                if command_name == 'mib_time_on_battery':
                    # Measured in seconds.
                    value = int(value)
                else:
                    # Measured in minutes.
                    value = int(value) * 60
                value_str = str(datetime.timedelta(seconds=int(value)))
                value_minute = float(value) / 60.0
                value = (value_minute, value_str)
            else:
                # Process time for apc
                value_items = re.sub(r'\(', '', value).split(')')
                if len(value_items) >= 2:
                    value_minute, value_str = value_items
                value = (int(value_minute)/60/60, value_str)
        if display:
            print('{}: {}'.format(snmp_mib_commands[command_name]['name'], value))
        return value

    def list_snmp_commands(self):
        for k, v in self.mib_commands.items():
            print('{}: Value: {}'.format(k, v['iso']))
            print('    Description: {}'.format(v['name']))
            if v['decode']:
                for k2, v2 in v['decode'].items():
                    print('        {}: {}'.format(k2, v2))

    def get_ups_list(self):
        return self.ups_list

    def read_ups_list(self):
        if not os.path.isfile(env.ut_const.UPS_LIST_JSON_FILE):
            print('Error: UPS List file not found: {}'.format(env.ut_const.UPS_LIST_JSON_FILE))
            return False
        with open(env.ut_const.UPS_LIST_JSON_FILE, 'r') as ups_list_file:
            self.ups_list = json.load(ups_list_file)
        return True

    def num_ups(self):
        cnt = 0
        for k in self.ups_list.keys():
            cnt += 1
        return cnt

    def check_ups_type(self, test_ups_type):
        if test_ups_type not in self.all_mib_cmds.keys():
            return False
        return True

    def list_valid_ups_types(self):
        return list(self.all_mib_cmds.keys())

    def print_log(self, fileptr):
        pass

    def print_log_header(self, fileptr):
        pass

    def print_table(self):
        pass


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
