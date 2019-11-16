#!/usr/bin/env python3
"""UPSmodule  -  utility for interacting with compatible UPSs

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
__version__ = "v0.9.0"
__maintainer__ = "RueiKe"
__status__ = "Beta Release"

import os
import sys
import re
import shlex
import time
import datetime
import json
import subprocess
from uuid import uuid4
try:
    from UPSmodules import env
except ModuleNotFoundError:
    import env
try:
    from config import (suspend_script, resume_script, shutdown_script, cancel_shutdown_script, read_interval,
                        threshold_battery_time_rem_crit, threshold_battery_time_rem_warn,
                        threshold_time_on_battery_crit, threshold_time_on_battery_warn,
                        threshold_battery_load_crit, threshold_battery_load_warn,
                        threshold_battery_capacity_crit, threshold_battery_capacity_warn)
except ModuleNotFoundError:
    print('The config.py file is missing or mis-configured.  Use config.py.template as a template.')
    print('Using defaults, which will not enable any daemon response scripts.')
    env.ut_const.ERROR_config = True


class UPSsnmp:
    def __init__(self):
        # UPS list from config.json for monitor and ls utils.
        self.ups_list = {}
        self.active_ups = {}

        # UPS response bit string decoders
        self.decoders = {'apc_system_status': ['Abnormal', 'OnBattery', 'LowBattery', 'OnLine', 'ReplaceBattery',
                                               'SCE', 'AVR_Boost', 'AVR_Trim', 'OverLoad', 'RT_Calibration',
                                               'BatteriesDischarged', 'ManualBypass', 'SoftwareBypass',
                                               'Bypass-InternalFault', 'Bypass-SupplyFailure', 'Bypass-FanFailure',
                                               'SleepOnTimer', 'SleepNoPower', 'On', 'Rebooting', 'BatterCommLost',
                                               'ShutdownInitiated', 'Boost/TrimFailure', 'BadOutVoltage',
                                               'BatteryChargerFail', 'HiBatTemp', 'WarnBatTemp', 'CritBatTemp',
                                               'SelfTestInProgress', 'LowBat/OnBat']}

        # UPS from config.py for ups-daemon and monitor utilities.
        self.daemon_params = {'suspend_script': '', 'resume_script': '',
                              'shutdown_script': '', 'cancel_shutdown_script': '',
                              'read_interval': env.ut_const.DEFAULT_DAEMON_READ_INTERVAL,
                              'threshold_battery_time_rem_crit': env.ut_const.def_threshold_battery_time_rem[0],
                              'threshold_battery_time_rem_warn': env.ut_const.def_threshold_battery_time_rem[1],
                              'threshold_time_on_battery_crit': env.ut_const.def_threshold_time_on_battery[0],
                              'threshold_time_on_battery_warn': env.ut_const.def_threshold_time_on_battery[1],
                              'threshold_battery_load_crit': env.ut_const.def_threshold_battery_load[0],
                              'threshold_battery_load_warn': env.ut_const.def_threshold_battery_load[1],
                              'threshold_battery_capacity_crit': env.ut_const.def_threshold_battery_capacity[0],
                              'threshold_battery_capacity_warn': env.ut_const.def_threshold_battery_capacity[1]
                              }

        # UPS MiB Commands
        self.monitor_mib_cmds = {'static': ['mib_ups_name', 'mib_ups_info', 'mib_bios_serial_number',
                                            'mib_firmware_revision', 'mib_ups_type', 'mib_ups_location',
                                            'mib_ups_uptime'],
                                 'dynamic': ['mib_battery_capacity', 'mib_time_on_battery',
                                             'mib_battery_runtime_remain', 'mib_input_voltage',
                                             'mib_input_frequency', 'mib_output_voltage', 'mib_output_frequency',
                                             'mib_output_load', 'mib_output_current', 'mib_output_power',
                                             'mib_system_status', 'mib_battery_status']}
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
                                                      'name': 'UPS Model Type',
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
                                     'mib_ups_uptime': {'iso': 'iso.3.6.1.2.1.1.3.0',
                                                        'name': 'UPS Up Time',
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
                                     'mib_system_status': {'iso': 'iso.3.6.1.4.1.318.1.1.1.11.1.1.0',
                                                           'name': 'UPS System Status',
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
                                                              'name': 'Battery Replacement',
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
                                                         'name': 'Output Load as % of Capacity',
                                                         'decode': None},
                                     'mib_output_power': {'iso': 'iso.3.6.1.4.1.318.1.1.1.4.2.8.0',
                                                          'name': 'Output Power in W',
                                                          'decode': None},
                                     'mib_output_current': {'iso': 'iso.3.6.1.4.1.318.1.1.1.4.2.4.0',
                                                            'name': 'Output Current in Amps',
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
                                                    'name': 'UPS Model Type',
                                                    'decode': None},
                                   'mib_ups_contact': {'iso': 'iso.3.6.1.2.1.1.4.0',
                                                       'name': 'UPS Contact',
                                                       'decode': None},
                                   'mib_ups_location': {'iso': 'iso.3.6.1.2.1.1.6.0',
                                                        'name': 'UPS Location',
                                                        'decode': None},
                                   'mib_ups_uptime': {'iso': 'iso.3.6.1.2.1.1.3.0',
                                                      'name': 'System Up Time',
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
                                                       'name': 'Output Load as % of Capacity',
                                                       'decode': None},
                                   'mib_output_current': {'iso': 'iso.3.6.1.4.1.935.10.1.1.2.18.1.4.1',
                                                          'name': 'Output Current in Amps',
                                                          'decode': None},
                                   'mib_output_power': {'iso': 'iso.3.6.1.4.1.935.10.1.1.2.18.1.5.1',
                                                        'name': 'Output Power in W',
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

        if self.read_ups_list():
            self.check_ups_list()
        else:
            print('Fatal Error: could not read json configuration file: {}'.format(env.ut_const.UPS_LIST_JSON_FILE))
            sys.exit(-1)
        # End of init

    # Read and check the UPS list.
    def read_ups_list(self):
        """Reads the config.json file which contains parameters for UPSs to be used by utility.

        :return: boolean True if no problems reading list
        """
        if not os.path.isfile(env.ut_const.UPS_LIST_JSON_FILE):
            print('Error: UPS List file not found: {}'.format(env.ut_const.UPS_LIST_JSON_FILE))
            return False
        with open(env.ut_const.UPS_LIST_JSON_FILE, 'r') as ups_list_file:
            self.ups_list = json.load(ups_list_file)
        return True

    def check_ups_list(self, quiet=True):
        """Check the list of UPS for compatibility, accessibility, and responsiveness.

        :param quiet: flag to specify if method should print results or return quietly
        :type quiet: bool
        :return:
        """
        daemon_cnt = 0
        ups_cnt = 0
        for k, v in self.ups_list.items():
            v['uuid'] = uuid4().hex
            v['accessible'] = False
            v['responsive'] = False
            v['mib_commands'] = None
            if self.check_ups_type(v['ups_type']):
                v['compatible'] = True
                if self.check_ip(v):
                    v['accessible'] = True
                    if self.check_snmp(v):
                        v['responsive'] = True
                        ups_cnt += 1
                        v['mib_commands'] = self.all_mib_cmds[v['ups_type']]
                if v['daemon']:
                    daemon_cnt += 1
                    self.active_ups = v
            else:
                v['compatible'] = False
                v['mib_commands'] = None
        if not quiet:
            print('config.json contains {} total UPSs and {} daemon UPS'.format(ups_cnt, daemon_cnt))
    # End of read and check the UPS list.

    # Methods to get, check, and list UPSs
    def get_name_for_ups_uuid(self, ups_uuid):
        """ Get the ups name for a given uuid
        :param ups_uuid: Universally unique identifier for a UPS
        :type ups_uuid: int
        """
        for k, v in self.ups_list.items():
            if v['uuid'] == ups_uuid:
                return str(k)
        return 'Error'

    def get_uuid_for_ups_name(self, ups_name):
        for k, v in self.ups_list.items():
            if v['display_name'] == ups_name:
                return v['uuid']
        return 'Error'

    def get_ups_list(self, errups=True):
        """Get the dictionary list of UPSs read at start up.
        :param errups: Flag to indicate if UPSs with errors should be inclduded
        :type errups: bool
        :return:  dictionary representing the list of UPSs
        """
        return_list = {}
        for ups_name, ups_item in self.ups_list.items():
            if not errups:
                if not self.is_responsive(ups_item):
                    continue
            return_list[ups_name] = ups_item
        return return_list

    def get_num_ups_tuple(self):
        """ This function will return a tuple of the UPS counts.
        :return: tuple represents listed, compatible, accessible, responsive UPSs
        """
        cnt = [0, 0, 0, 0]
        for k, v in self.ups_list.items():
            cnt[0] += 1
            if self.is_compatible(v):
                cnt[1] += 1
            if self.is_accessible(v):
                cnt[2] += 1
            if self.is_responsive(v):
                cnt[3] += 1
        return tuple(cnt)

    def check_ups_type(self, test_ups_type):
        """ Checks if the given UPS type is valid
        :param test_ups_type:  A string representation of the ups type
        :type test_ups_type: str
        :return: bool where True indicates the ups type is valid
        """
        if test_ups_type not in self.all_mib_cmds.keys():
            return False
        return True

    def list_valid_ups_types(self):
        """ Return a list of valid ups types
        :return: list of str representing valid ups types
        """
        return list(self.all_mib_cmds.keys())
    # End of methods to get, check, and list UPSs

    # Methods to set daemon and active UPS.
    def set_daemon_ups(self):
        for k, v in self.ups_list.items():
            if v['daemon']:
                self.active_ups = v
                return True
        return False

    def set_active_ups(self, ups_item):
        self.active_ups = ups_item
    # End of methods to set daemon and active UPS.

    # Set of methods to return parameters for target UPS.
    def get_ups_parameter_value(self, param_name, tups):
        if not tups:
            tups = self.active_ups
        if param_name in tups.keys():
            return tups[param_name]
        else:
            return None

    # TODO test this and use where command name is needed.
    def get_mib_commands(self, tups=None):
        if not tups:
            tups = self.active_ups
        return tups['mib_commands']

    # TODO test this and use where command name is needed.
    def get_mib_name(self, mib_cmd, tups=None):
        """Get the mib command name.

        :param mib_cmd: string representing mib command
        :param tups: target UPS, active UPS if missing
        :return: string of mib command name
        """
        if not tups:
            tups = self.active_ups
        if mib_cmd in tups['mib_commands'].keys():
            return tups['mib_commands'][mib_cmd]['name']
        else:
            return mib_cmd

    def get_mib_name_for_type(self, mib_cmd, ups_type):
        """Get mib command name for a given UPS type.

        :param mib_cmd:
        :param ups_type:
        :return: string of mib command name
        """
        return self.all_mib_cmds[ups_type][mib_cmd]['name']

    def ups_uuid(self, tups=None):
        if not tups:
            tups = self.active_ups
        return tups['uuid']

    def ups_name(self, tups=None):
        if not tups:
            tups = self.active_ups
        return tups['display_name']

    def ups_type(self, tups=None):
        if not tups:
            tups = self.active_ups
        return tups['ups_type']

    def ups_ip(self, tups=None):
        if not tups:
            tups = self.active_ups
        return tups['ups_IP']
    # End of set of methods to return parameters for target UPS.

    # Set of methods to check if UPS is valid.
    def check_ip(self, tups=None):
        if not tups:
            tups = self.active_ups
        if not os.system('ping -c 1 {} > /dev/null'.format(tups['ups_IP'])):
            return True
        return False

    def check_snmp(self, tups=None):
        if not tups:
            tups = self.active_ups
        cmd_str = 'snmpget -v2c -c {} {} {}'.format(tups['snmp_community'], tups['ups_IP'], 'iso.3.6.1.2.1.1.1.0')

        try:
            snmp_output = subprocess.check_output(shlex.split(cmd_str), shell=False,
                                                  stderr=subprocess.DEVNULL).decode().split('\n')
            if env.ut_const.DEBUG: print(snmp_output)
        except:
            return False
        return True

    def is_compatible(self, v=None):
        if not v:
            v = self.active_ups
        return v['compatible']

    def is_responsive(self, v=None):
        if not v:
            v = self.active_ups
        return v['responsive']

    def is_accessible(self, v=None):
        if not v:
            v = self.active_ups
        return v['accessible']
    # End of set of methods to check if UPS is valid.

    # Commands to read from UPS using snmp protocol.
    def get_monitor_mib_commands(self, cmd_type='dynamic'):
        if cmd_type == 'all':
            return_list = []
            for cmd_type in ['static', 'dynamic']:
                for item in self.monitor_mib_cmds[cmd_type]:
                    return_list.append(item)
            return return_list
        else:
            return self.monitor_mib_cmds[cmd_type]

    def read_all_ups_list_items(self, command_list, errups=True):
        results = {}
        for ups_name, ups_item in self.get_ups_list().items():
            if not errups:
                if not self.is_responsive(ups_item):
                    continue
            self.set_active_ups(ups_item)
            results[ups_name] = self.read_ups_list_items(command_list)
        return results

    def read_ups_list_items(self, command_list):
        results = {'display_name': self.ups_name(),
                   'name': self.ups_name(),
                   'uuid': self.ups_uuid(),
                   'ups_IP': self.ups_ip(),
                   'ups_type': self.ups_type()}
        for cmd in command_list:
            results[cmd] = self.send_snmp_command(cmd)
        return results

    def send_snmp_command(self, command_name, target_ups=None, display=False):
        if not target_ups:
            target_ups = self.active_ups
        if not self.is_responsive(target_ups):
            return 'Invalid UPS'
        snmp_mib_commands = self.get_mib_commands(target_ups)
        if command_name not in snmp_mib_commands:
            return 'No data'
        cmd_mib = snmp_mib_commands[command_name]['iso']
        cmd_str = 'snmpget -v2c -c {} {} {}'.format(target_ups['snmp_community'],
                                                    target_ups['ups_IP'], cmd_mib)
        try:
            snmp_output = subprocess.check_output(shlex.split(cmd_str), shell=False,
                                                  stderr=subprocess.DEVNULL).decode().split('\n')
        except:
            print('Error executing snmp command to {} at {}.'.format(self.ups_name(), self.ups_ip()))
            return 'UPS Not Responding'

        value = ''
        value_minute = -1
        value_str = 'UNK'
        for line in snmp_output:
            if env.ut_const.DEBUG: print('line:  {}'.format(line))
            if re.match(r'.*=.*:.*', line):
                value = line.split(':', 1)[1]
                value = re.sub(r'\"', '', value).strip()
        if snmp_mib_commands[command_name]['decode']:
            if value in snmp_mib_commands[command_name]['decode'].keys():
                value = snmp_mib_commands[command_name]['decode'][value]
        if target_ups['ups_type'] == 'eaton-pw':
            if command_name == 'mib_output_voltage' or command_name == 'mib_output_frequency':
                value = int(value) / 10.0
            elif command_name == 'mib_output_current':
                value = int(value) / 10.0
            elif command_name == 'mib_input_voltage' or command_name == 'mib_input_frequency':
                value = int(value) / 10.0
            elif command_name == 'mib_system_temperature':
                value = int(value) / 10.0
        if command_name == 'mib_system_status' and target_ups['ups_type'] == 'apc-ap9630':
            value = self.bit_str_decoder(value, self.decoders['apc_system_status'])
        if command_name == 'mib_time_on_battery' or command_name == 'mib_battery_runtime_remain':
            # Create a minute, string tuple
            if target_ups['ups_type'] == 'eaton-pw':
                # Process time for eaton-pw
                if command_name == 'mib_time_on_battery':
                    # Measured in seconds.
                    value = int(value)
                else:
                    # Measured in minutes.
                    value = int(value) * 60
                value_str = str(datetime.timedelta(seconds=int(value)))
                value_minute = round(float(value) / 60.0, 2)
                value = (value_minute, value_str)
            else:
                # Process time for apc
                value_items = re.sub(r'\(', '', value).split(')')
                if len(value_items) >= 2:
                    value_minute, value_str = value_items
                value = (round(int(value_minute)/60/60, 2), value_str)
        if display:
            print('{}: {}'.format(snmp_mib_commands[command_name]['name'], value))
        return value

    @staticmethod
    def bit_str_decoder(value, decode_key):
        """ Bit string decoder
            
            :param value: A string representing a bit encoded set of flags
            :param decode_key: A list representing the meaning of a 1 for each bit field
            :returns: A string of concatenated bit decode strings 
        """
        value_str = ''
        for index, bit_value in enumerate(value):
            if index > len(decode_key):
                break
            if bit_value == '1':
                if value_str == '':
                    value_str = decode_key[index]
                else:
                    value_str = '{}-{}'.format(value_str, decode_key[index])
        return value_str

    def print_snmp_commands(self, tups=None):
        if not tups:
            tups = self.active_ups
        for k, v in self.get_mib_commands(tups).items():
            print('{}: Value: {}'.format(k, v['iso']))
            print('    Description: {}'.format(v['name']))
            if v['decode']:
                for k2, v2 in v['decode'].items():
                    print('        {}: {}'.format(k2, v2))
    # End of commands to read from UPS using snmp protocol.

    # Set parameters required for daemon mode.
    def set_daemon_parameters(self):
        if env.ut_const.ERROR_config:
            print('Error in config.py file.  Using defaults')
            return

        # Set script definitions
        if isinstance(suspend_script, str):
            self.daemon_params['suspend_script'] = suspend_script
            if suspend_script:
                if not os.path.isfile(suspend_script):
                    print('Missing suspend script: {}'.format(suspend_script))
                    sys.exit(-1)
        if isinstance(resume_script, str):
            self.daemon_params['resume_script'] = resume_script
            if resume_script:
                if not os.path.isfile(resume_script):
                    print('Missing resume script: {}'.format(resume_script))
                    sys.exit(-1)
        if isinstance(shutdown_script, str):
            self.daemon_params['shutdown_script'] = shutdown_script
            if shutdown_script:
                if not os.path.isfile(shutdown_script):
                    print('Missing shutdown script: {}'.format(shutdown_script))
                    sys.exit(-1)
        if isinstance(cancel_shutdown_script, str):
            self.daemon_params['cancel_shutdown_script'] = cancel_shutdown_script
            if cancel_shutdown_script:
                if not os.path.isfile(cancel_shutdown_script):
                    print('Missing cancel shutdown script: {}'.format(cancel_shutdown_script))

        # Set daemon read interval
        if isinstance(read_interval, int):
            if read_interval >= env.ut_const.READ_INTERVAL_LIMIT:
                self.daemon_params['read_interval'] = read_interval
            else:
                print('Invalid read interval in config.py.  Using default.')
                
        # Battery Time Remaining
        if isinstance(threshold_battery_time_rem_crit, int):
            if threshold_battery_time_rem_crit >= env.ut_const.def_threshold_battery_time_rem[2]:
                self.daemon_params['threshold_battery_time_rem_crit'] = threshold_battery_time_rem_crit
            else:
                print('Invalid threshold_battery_time_rem_crit in config.py.  Using default.')
        if isinstance(threshold_battery_time_rem_warn, int):
            if self.daemon_params['threshold_battery_time_rem_crit'] < threshold_battery_time_rem_warn:
                self.daemon_params['threshold_battery_time_rem_warn'] = threshold_battery_time_rem_warn
            else:
                print('Invalid threshold_battery_time_rem_warn in config.py.  Using default.')
                
        # Time on Battery        
        if isinstance(threshold_time_on_battery_warn, int):
            if threshold_time_on_battery_warn >= env.ut_const.def_threshold_time_on_battery[2]:
                self.daemon_params['threshold_time_on_battery_warn'] = threshold_time_on_battery_warn
            else:
                print('Invalid threshold_time_battery_warn in config.py.  Using default.')
        if isinstance(threshold_time_on_battery_crit, int):
            if threshold_time_on_battery_crit > self.daemon_params['threshold_time_on_battery_warn']:
                self.daemon_params['threshold_time_on_battery_crit'] = threshold_time_on_battery_crit
            else:
                print('Invalid threshold_time_battery_crit in config.py.  Using default.')

        # Battery Load
        if isinstance(threshold_battery_load_warn, int):
            if env.ut_const.def_threshold_battery_load[2] < threshold_battery_load_warn < 100:
                self.daemon_params['threshold_battery_load_warn'] = threshold_battery_load_warn
            else:
                print('Invalid threshold_battery_load_warn in config.py.  Using default.')
        if isinstance(threshold_battery_load_crit, int):
            if self.daemon_params['threshold_battery_load_warn'] < threshold_battery_load_crit <= 100:
                self.daemon_params['threshold_battery_load_crit'] = threshold_battery_load_crit
            else:
                print('Invalid threshold_battery_load_crit in config.py.  Using default.')

        # Battery Capacity
        if isinstance(threshold_battery_capacity_crit, int):
            if env.ut_const.def_threshold_battery_capacity[2] < threshold_battery_capacity_crit < 100:
                self.daemon_params['threshold_battery_capacity_crit'] = threshold_battery_capacity_crit
            else:
                print('Invalid threshold_battery_capacity_crit in config.py.  Using default.')
        if isinstance(threshold_battery_capacity_warn, int):
            if self.daemon_params['threshold_battery_capacity_crit'] < threshold_battery_capacity_warn <= 100:
                self.daemon_params['threshold_battery_capacity_warn'] = threshold_battery_capacity_warn
            else:
                print('Invalid threshold_battery_capacity_warn in config.py.  Using default.')

    def print_daemon_parameters(self):
        print('Daemon parameters:')
        for k, v in self.daemon_params.items():
            print('    {}: {}'.format(k, v))

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

    def cancel_shutdown(self):
        if not self.daemon_params['cancel_shutdown_script']:
            print('No cancel shutdown script defined')
            return
        try:
            cmd = subprocess.Popen(shlex.split(self.daemon_params['cancel_shutdown_script']),
                                   shell=False, stdout=subprocess.PIPE)
            while True:
                if cmd.poll() is not None:
                    break
                time.sleep(1)
        except:
            print('Error: could not execute cancel shutdown script: {}'.format(
                  self.daemon_params['cancel_shutdown_script']), file=sys.stderr)

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
    # End of set parameters required for daemon mode.


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
