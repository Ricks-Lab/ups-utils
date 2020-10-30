#!/usr/bin/env python3
"""UPSmodule  -  utility for interacting with compatible UPSs

    Copyright (C) 2019  RicksLab

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
__copyright__ = "Copyright (C) 2019 RicksLab"
__credits__ = ['Natalya Langford - Configuration Parser']
__license__ = "GNU General Public License"
__program_name__ = "ups-utils"
__maintainer__ = "RueiKe"
__docformat__ = 'reStructuredText'
# pylint: disable=multiple-statements
# pylint: disable=line-too-long
# pylint: disable=bad-continuation

import os
import sys
import re
import shlex
import time
import datetime
import json
import subprocess
import logging
import configparser
from enum import Enum
from typing import Tuple, List, Union, Dict
from uuid import uuid4
from UPSmodules import __version__, __status__
try:
    from UPSmodules import env
except ModuleNotFoundError:
    import env


LOGGER = logging.getLogger('ups-utils')


class UPSsnmp:
    """ Class definition for UPS communication object."""

    # Configuration details
    daemon_paths = ['boinc_home', 'ups_utils_script_path']
    daemon_scripts = ['suspend_script', 'resume_script', 'shutdown_script', 'cancel_shutdown_script']
    daemon_param_names = ['read_interval', 'threshold_battery_time_rem', 'threshold_time_on_battery',
                          'threshold_battery_load', 'threshold_battery_capacity']
    daemon_param_defaults = {'ups_utils_script_path': os.path.expanduser('~/.local/bin/'),
                             'read_interval': {'monitor': 10, 'daemon': 30, 'limit': 5},
                             'threshold_battery_time_rem': {'crit': 5, 'warn': 10, 'limit': 4},
                             'threshold_time_on_battery': {'crit': 5, 'warn': 3, 'limit': 1},
                             'threshold_battery_load': {'crit': 90, 'warn': 80, 'limit': 10},
                             'threshold_battery_capacity': {'crit': 10, 'warn': 50, 'limit': 5}}
    # Set params to defaults
    daemon_params: Dict[str, Union[str, dict]] = {
        'ups_ini_file': 'DEFAULTS',
        'ups_json_file': 'NONE',
        'boinc_home': None, 'ups_utils_script_path': daemon_param_defaults['ups_utils_script_path'],
        'suspend_script': None, 'resume_script': None,
        'shutdown_script': None, 'cancel_shutdown_script': None,
        'read_interval': daemon_param_defaults['read_interval'].copy(),
        'threshold_battery_time_rem': daemon_param_defaults['threshold_battery_time_rem'].copy(),
        'threshold_time_on_battery': daemon_param_defaults['threshold_time_on_battery'].copy(),
        'threshold_battery_load': daemon_param_defaults['threshold_battery_load'].copy(),
        'threshold_battery_capacity': daemon_param_defaults['threshold_battery_capacity'].copy()}

    state_style = Enum('state', 'warn crit green bold normal')
    # UPS response bit string decoders
    decoders = {'apc_system_status': ['Abnormal', 'OnBattery', 'LowBattery', 'OnLine', 'ReplaceBattery',
                                      'SCE', 'AVR_Boost', 'AVR_Trim', 'OverLoad', 'RT_Calibration',
                                      'BatteriesDischarged', 'ManualBypass', 'SoftwareBypass',
                                      'Bypass-InternalFault', 'Bypass-SupplyFailure', 'Bypass-FanFailure',
                                      'SleepOnTimer', 'SleepNoPower', 'On', 'Rebooting', 'BatterCommLost',
                                      'ShutdownInitiated', 'Boost/TrimFailure', 'BadOutVoltage',
                                      'BatteryChargerFail', 'HiBatTemp', 'WarnBatTemp', 'CritBatTemp',
                                      'SelfTestInProgress', 'LowBat/OnBat', 'ShutdownFromUpstream',
                                      'ShutdownFromDownstream', 'NoBatteriesAttached', 'SyncCmdsInProg',
                                      'SyncSleepInProg', 'SyncRebootInProg', 'InvDCimbalance',
                                      'TransferReadyFailure', 'Shutdown/Unable to Transfer',
                                      'LowBatShutdown', 'FanFail', 'MainRelayFail', 'BypassRelayFail',
                                      'TempBypass', 'HighInternalTemp', 'BatTempSensorFault',
                                      'InputOORforBypass', 'DCbusOverV', 'PFCfailure', 'CritHWfail',
                                      'Green/ECO mode', 'HotStandby', 'EPO', 'LoadAlarmViolation',
                                      'BypassPhaseFault', 'UPSinternalComFail', 'EffBoosterMode',
                                      'Off', 'Standby', 'Minor/EnvAlarm']}

    # UPS MiB Commands
    monitor_mib_cmds = {'static': ['mib_ups_name', 'mib_ups_info', 'mib_bios_serial_number',
                                   'mib_firmware_revision', 'mib_ups_type', 'mib_ups_location',
                                   'mib_ups_uptime'],
                        'dynamic': ['mib_battery_capacity', 'mib_time_on_battery',
                                    'mib_battery_runtime_remain', 'mib_input_voltage',
                                    'mib_input_frequency', 'mib_output_voltage', 'mib_output_frequency',
                                    'mib_output_load', 'mib_output_current', 'mib_output_power',
                                    'mib_system_status', 'mib_battery_status']}
    output_mib_cmds = ['mib_output_voltage', 'mib_output_frequency', 'mib_output_load', 'mib_output_current',
                       'mib_output_power']
    input_mib_cmds = ['mib_input_voltage', 'mib_input_frequency']

    all_mib_cmds = {
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
                     'mib_input_voltage': {'iso': 'iso.3.6.1.4.1.935.10.1.1.2.16.1.3.1',
                                           'name': 'Input Voltage V',
                                           'decode': None},
                     'mib_input_frequency': {'iso': 'iso.3.6.1.4.1.935.10.1.1.2.16.1.2.1',
                                             'name': 'Input Frequency Hz',
                                             'decode': None},
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

    def __init__(self):
        # UPS list from ups-config.json for monitor and ls utils.
        self.ups_list = {}
        self.active_ups = {}

        if self.read_ups_list():
            self.check_ups_list()
        else:
            print('Error reading {} file: {}'.format(env.UT_CONST.UPS_JSON_FILE, env.UT_CONST.ups_json_file))
            sys.exit(-1)
        # End of init

    def __str__(self):
        str_rep = ''
        for name, value in self.ups_list.items():
            if str_rep:
                str_rep = '{}\n{}:\n'.format(str_rep, name)
            else:
                str_rep = '{}:\n'.format(name)
            for ups_param_name, ups_param_value in value.items():
                str_rep = '{}\n    {}: {}\n'.format(str_rep, ups_param_name, ups_param_value)
        return str_rep

    # Read and check the UPS list.
    def read_ups_list(self) -> bool:
        """Reads the ups-config.json file which contains parameters for UPSs to be used by utility.

        :return: boolean True if no problems reading list
        """
        if not env.UT_CONST.ups_json_file or not os.path.isfile(env.UT_CONST.ups_json_file):
            print('Error: {} file not found: {}'.format(env.UT_CONST.UPS_JSON_FILE, env.UT_CONST.ups_json_file))
            return False
        try:
            with open(env.UT_CONST.ups_json_file, 'r') as ups_list_file:
                self.ups_list = json.load(ups_list_file)
        except FileNotFoundError as error:
            env.UT_CONST.log_print("Error: file not found error for [{}]: {}".format(env.UT_CONST.ups_json_file, error))
            return False
        except PermissionError as error:
            env.UT_CONST.ups_json_file("Error: permission error for [{}]: {}".format(env.UT_CONST.ups_json_file, error))
            return False
        self.daemon_params['ups_json_file'] = env.UT_CONST.ups_json_file
        return True

    def check_ups_list(self, quiet: bool = True) -> None:
        """Check the list of UPS for compatibility, accessibility, and responsiveness.

        :param quiet: flag to specify if method should print results or return quietly
        :return: None
        """
        daemon_cnt = 0
        ups_cnt = 0
        error_flag = False
        for ups in self.ups_list.values():
            ups['uuid'] = uuid4().hex
            if not re.search(env.UT_CONST.PATTERNS['IPV4'], ups['ups_IP']):
                if not re.search(env.UT_CONST.PATTERNS['FQDN'], ups['ups_IP']):
                    if not re.search(env.UT_CONST.PATTERNS['IPV6'], ups['ups_IP']):
                        env.UT_CONST.log_print('ERROR: IP Address entry [{}]'.format(ups['ups_IP']))
                        error_flag = True
                        continue
            ups['compatible'] = False
            ups['accessible'] = False
            ups['responsive'] = False
            ups['mib_commands'] = None
            if self.check_ups_type(ups['ups_type']):
                ups['compatible'] = True
                if self.check_ip(ups):
                    ups['accessible'] = True
                    if self.check_snmp(ups):
                        ups['responsive'] = True
                        ups_cnt += 1
                        ups['mib_commands'] = self.all_mib_cmds[ups['ups_type']]
                if ups['daemon']:
                    daemon_cnt += 1
                    self.active_ups = ups
            else:
                ups['compatible'] = False
                ups['mib_commands'] = None
        if not quiet:
            print('{} contains {} total UPSs and {} daemon UPS'.format(env.UT_CONST.ups_json_file,
                                                                       ups_cnt, daemon_cnt))
        if error_flag:
            env.UT_CONST.log_print('FATAL ERROR: Invalid entry in {}'.format(env.UT_CONST.ups_json_file))
            sys.exit(-1)
    # End of read and check the UPS list.

    # Methods to get, check, and list UPSs
    def get_name_for_ups_uuid(self, ups_uuid: int) -> str:
        """ Get the ups name for a given uuid

        :param ups_uuid: Universally unique identifier for a UPS
        :return: name of the ups
        """
        for name, ups in self.ups_list.items():
            if ups['uuid'] == ups_uuid:
                return str(name)
        return 'Error'

    def get_uuid_for_ups_name(self, ups_name: str) -> str:
        """ Get uuid for ups with given name.

        :param ups_name: The target ups name.
        :return: The uuid as str or 'Error' if not found
        """
        for ups in self.ups_list.values():
            if ups['display_name'] == ups_name:
                return ups['uuid']
        return 'Error'

    def get_ups_list(self, errups: bool = True) -> dict:
        """Get the dictionary list of UPSs read at start up.

        :param errups: Flag to indicate if UPSs with errors should be included
        :return:  dictionary representing the list of UPSs
        """
        return_list = {}
        for ups_name, ups_item in self.ups_list.items():
            if not errups:
                if not self.is_responsive(ups_item):
                    continue
            return_list[ups_name] = ups_item
        return return_list

    def get_num_ups_tuple(self) -> Tuple[int]:
        """ This function will return a tuple of the UPS counts.

        :return: tuple represents listed, compatible, accessible, responsive UPSs
        """
        cnt = [0, 0, 0, 0]
        for ups in self.ups_list.values():
            cnt[0] += 1
            if self.is_compatible(ups):
                cnt[1] += 1
            if self.is_accessible(ups):
                cnt[2] += 1
            if self.is_responsive(ups):
                cnt[3] += 1
        return tuple(cnt)

    def check_ups_type(self, test_ups_type: str) -> bool:
        """ Checks if the given UPS type is valid

        :param test_ups_type:  A string representation of the ups type
        :return: True indicates the ups type is valid
        """
        if test_ups_type not in self.all_mib_cmds.keys():
            return False
        return True

    def list_valid_ups_types(self) -> List[str]:
        """ Return a list of valid ups types

        :return: list of str representing valid ups types
        """
        return list(self.all_mib_cmds.keys())
    # End of methods to get, check, and list UPSs

    # Methods to set daemon and active UPS.
    def set_daemon_ups(self) -> bool:
        """ Set the active ups to the daemon ups.

        :return: True if active UPS setting is a success
        """
        for ups in self.ups_list.values():
            if ups['daemon']:
                self.active_ups = ups
                return True
        return False

    def set_active_ups(self, ups_item: dict) -> None:
        """ Sets the active ups to the specified ups.

        :param ups_item: The target ups
        :return: None
        """
        self.active_ups = ups_item
    # End of methods to set daemon and active UPS.

    # Set of methods to return parameters for target UPS.
    def get_ups_parameter_value(self, param_name: str, tups: dict) -> Union[str, None]:
        """ Get ups parameter value for parameter name from target UPS or active UPS if not specified

        :param param_name: Target parameter name
        :param tups: Target UPS dict
        :return: Parameter value as string else None
        """
        if not tups:
            tups = self.active_ups
        return tups[param_name] if param_name in tups.keys() else None

    def get_mib_commands(self, tups: dict = None) -> dict:
        """ Get the list of MIB commands for the target UPS.

        :param tups:
        :return: List of MIB commands for target UPS
        """
        if not tups:
            tups = self.active_ups
        return tups['mib_commands']

    def get_mib_name(self, mib_cmd: str, tups: dict = None) -> str:
        """Get the mib command name.

        :param mib_cmd: string representing mib command
        :param tups: target UPS, active UPS if missing
        :return: string of mib command name
        """
        if not tups:
            tups = self.active_ups
        if mib_cmd in tups['mib_commands'].keys():
            return tups['mib_commands'][mib_cmd]['name']
        return mib_cmd

    def get_mib_name_for_type(self, mib_cmd: str, ups_type: str) -> str:
        """Get mib command name for a given UPS type.

        :param mib_cmd:
        :param ups_type:
        :return: string of mib command name
        """
        return self.all_mib_cmds[ups_type][mib_cmd]['name']

    def ups_uuid(self, tups: dict = None) -> int:
        """ Get the uuid value for the target UPS or active UPS if target is None.

        :param tups:  The target ups dictionary from list or None.
        :return:  The uuid as an int.
        """
        if not tups:
            tups = self.active_ups
        return tups['uuid']

    def ups_name(self, tups: dict = None) -> str:
        """ Get the name value for the target UPS or active UPS if target is None.

        :param tups:  The target ups dictionary from list or None.
        :return:  The name as an str.
        """
        if not tups:
            tups = self.active_ups
        return tups['display_name']

    def ups_type(self, tups: dict = None) -> str:
        """ Get the type value for the target UPS or active UPS if target is None.

        :param tups:  The target ups dictionary from list or None.
        :return:  The ups_type as an str.
        """
        if not tups:
            tups = self.active_ups
        return tups['ups_type']

    def ups_ip(self, tups: dict = None) -> None:
        """ Get the IP address value for the target UPS or active UPS if target is None.

        :param tups:  The target ups dictionary from list or None.
        :return:  The IP address as an str.
        """
        if not tups:
            tups = self.active_ups
        return tups['ups_IP']
    # End of set of methods to return parameters for target UPS.

    # Set of methods to check if UPS is valid.
    def check_ip(self, tups: dict = None) -> bool:
        """ check the IP address value for the target UPS or active UPS if target is None.

        :param tups:  The target ups dictionary from list or None.
        :return:  True if the given IP address is pingable, else False
        """
        if not tups:
            tups = self.active_ups
        return not bool(os.system('ping -c 1 {} > /dev/null'.format(tups['ups_IP'])))

    def check_snmp(self, tups: dict = None) -> bool:
        """ check if the IP address for the target UPS or active UPS if target is None, responds to snmp command.

        :param tups:  The target ups dictionary from list or None.
        :return:  True if the given IP address responds, else False
        """
        if not tups:
            tups = self.active_ups
        cmd_str = 'snmpget -v2c -c {} {} {}'.format(tups['snmp_community'], tups['ups_IP'], 'iso.3.6.1.2.1.1.1.0')

        try:
            snmp_output = subprocess.check_output(shlex.split(cmd_str), shell=False,
                                                  stderr=subprocess.DEVNULL).decode().split('\n')
            LOGGER.debug(snmp_output)
        except subprocess.CalledProcessError as err:
            LOGGER.debug('%s execution error: %s', cmd_str, err)
            return False
        return True

    def is_compatible(self, tups: dict = None) -> bool:
        """ check if target UPS or active UPS if target is None, is compatible.

        :param tups:  The target ups dictionary from list or None.
        :return:  True if compatible
        """
        if not tups:
            tups = self.active_ups
        return tups['compatible']

    def is_responsive(self, tups: dict = None) -> bool:
        """ check if target UPS or active UPS if target is None, is responsive.

        :param tups:  The target ups dictionary from list or None.
        :return:  True if responsive
        """
        if not tups:
            tups = self.active_ups
        return tups['responsive']

    def is_accessible(self, tups: dict = None) -> bool:
        """ check if target UPS or active UPS if target is None, is accessible.

        :param tups:  The target ups dictionary from list or None.
        :return:  True if accessible
        """
        if not tups:
            tups = self.active_ups
        return tups['accessible']
    # End of set of methods to check if UPS is valid.

    # Commands to read from UPS using snmp protocol.
    def get_monitor_mib_commands(self, cmd_type: str = 'dynamic') -> list:
        """ Get the specified list of monitor mib commands for the active UPS.

        :param cmd_type:  The target type of monitor commands
        :return:  list of relevant mib commands
        """
        if cmd_type == 'all':
            return_list = []
            for try_cmd_type in ['static', 'dynamic']:
                for item in self.monitor_mib_cmds[try_cmd_type]:
                    return_list.append(item)
            return return_list
        return self.monitor_mib_cmds[cmd_type]

    def read_all_ups_list_items(self, command_list: list, errups: bool = True) -> dict:
        """ Get the specified list of monitor mib commands for all UPSs.

        :param command_list:  A list of mib commands to be read from the active UPS
        :param errups: Flag to indicate if error UPS should be included.
        :return:  dict of results from the reading of all commands from all UPSs.
        """
        results = {}
        for ups_name, ups_item in self.get_ups_list().items():
            if not errups:
                if not self.is_responsive(ups_item):
                    continue
            self.set_active_ups(ups_item)
            results[ups_name] = self.read_ups_list_items(command_list)
        return results

    def read_ups_list_items(self, command_list: list, tups: dict = None) -> dict:
        """ Read the specified list of monitor mib commands for all UPSs.

        :param command_list:  A list of mib commands to be read from the active UPS
        :param tups:  The target ups dictionary from list or None.
        :return:  dict of results from the reading of all commands target UPS.
        """
        if not tups:
            tups = self.active_ups
        results = {'valid': True,
                   'display_name': self.ups_name(tups=tups),
                   'name': self.ups_name(tups=tups),
                   'uuid': self.ups_uuid(tups=tups),
                   'ups_IP': self.ups_ip(tups=tups),
                   'ups_type': self.ups_type(tups=tups)}
        for cmd in command_list:
            results[cmd] = self.send_snmp_command(cmd, tups=tups)
            if not results[cmd]:
                results['valid'] = False
                break
        # Since PowerWalker NMC is not intended for 110V UPSs, the following correction to output current is needed.
        if self.ups_type(tups=tups) == 'eaton-pw':
            if 'mib_output_current' in results.keys() and 'mib_output_voltage' in results.keys():
                results['mib_output_current'] = round((230/results['mib_output_voltage']) *
                                                      results['mib_output_current'], 1)
        return results

    def send_snmp_command(self, command_name: str, tups: dict = None,
                          display: bool = False) -> Union[str, int, List[Union[float, str]], float, None]:
        """ Read the specified mib commands results for specified UPS or active UPS if not specified.

        :param command_name:  A command to be read from the target UPS
        :param tups:  The target ups dictionary from list or None.
        :param display: If true the results will be printed
        :return:  The results from the read, could be str, int or tuple
        """
        if not tups:
            tups = self.active_ups
        if not self.is_responsive(tups):
            return 'Invalid UPS'
        snmp_mib_commands = self.get_mib_commands(tups)
        if command_name not in snmp_mib_commands:
            return 'No data'
        cmd_mib = snmp_mib_commands[command_name]['iso']
        cmd_str = 'snmpget -v2c -c {} {} {}'.format(tups['snmp_community'], tups['ups_IP'], cmd_mib)
        try:
            snmp_output = subprocess.check_output(shlex.split(cmd_str), shell=False,
                                                  stderr=subprocess.DEVNULL).decode().split('\n')
        except subprocess.CalledProcessError:
            LOGGER.debug('Error executing snmp command to %s at %s.', self.ups_name(), self.ups_ip())
            return None

        value = ''
        value_minute = -1
        value_str = 'UNK'
        for line in snmp_output:
            if not line: continue
            LOGGER.debug('line: %s', line)
            if re.match(env.UT_CONST.PATTERNS['SNMP_VALUE'], line):
                value = line.split(':', 1)[1]
                value = re.sub(r'\"', '', value).strip()
        if snmp_mib_commands[command_name]['decode']:
            if value in snmp_mib_commands[command_name]['decode'].keys():
                value = snmp_mib_commands[command_name]['decode'][value]
        if tups['ups_type'] == 'eaton-pw':
            if command_name == 'mib_output_voltage' or command_name == 'mib_output_frequency':
                value = int(value) / 10.0
            elif command_name == 'mib_output_current':
                value = int(value) / 10.0
            elif command_name == 'mib_input_voltage' or command_name == 'mib_input_frequency':
                value = int(value) / 10.0
            elif command_name == 'mib_system_temperature':
                value = int(value) / 10.0
        if command_name == 'mib_system_status' and tups['ups_type'] == 'apc-ap9630':
            value = self.bit_str_decoder(value, self.decoders['apc_system_status'])
        if command_name == 'mib_time_on_battery' or command_name == 'mib_battery_runtime_remain':
            # Create a minute, string tuple
            if tups['ups_type'] == 'eaton-pw':
                # Process time for eaton-pw
                if command_name == 'mib_time_on_battery':
                    # Measured in seconds.
                    value = int(value)
                else:
                    # Measured in minutes.
                    value = int(value) * 60
                value_str = str(datetime.timedelta(seconds=int(value)))
                value_minute = round(float(value) / 60.0, 2)
                value = [value_minute, value_str]
            else:
                # Process time for apc
                value_items = re.sub(r'\(', '', value).split(')')
                if len(value_items) >= 2:
                    value_minute, value_str = value_items
                value = (round(int(value_minute)/60/60, 2), value_str)
        if display:
            if command_name == 'mib_output_current' and tups['ups_type'] == 'eaton-pw':
                print('{}: {} - raw, uncorrected value.'.format(snmp_mib_commands[command_name]['name'], value))
            else:
                print('{}: {}'.format(snmp_mib_commands[command_name]['name'], value))
        return value

    @staticmethod
    def bit_str_decoder(value: str, decode_key: list) -> str:
        """ Bit string decoder

        :param value: A string representing a bit encoded set of flags
        :param decode_key: A list representing the meaning of a 1 for each bit field
        :return: A string of concatenated bit decode strings
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

    def print_decoders(self) -> None:
        """ Prints all bit decoders.

        :return: None
        """
        for decoder_name, decoder_list in self.decoders.items():
            print('decode key: {}'.format(decoder_name))
            for i, item in enumerate(decoder_list, start=1):
                print('  {:2d}: {}'.format(i, item))

    def print_snmp_commands(self, tups: dict = None) -> None:
        """ Print all supported mib commands for the target UPS, which is the active UPS when not specified.

        :param tups:  The target ups dictionary from list or None.
        :return:  None
        """
        if not tups:
            tups = self.active_ups
        for mib_name, mib_dict in self.get_mib_commands(tups).items():
            print('{}: Value: {}'.format(mib_name, mib_dict['iso']))
            print('    Description: {}'.format(mib_dict['name']))
            if mib_dict['decode']:
                for decoder_name, decoder_list in mib_dict['decode'].items():
                    print('        {}: {}'.format(decoder_name, decoder_list))
    # End of commands to read from UPS using snmp protocol.

    # Set parameters required for daemon mode.
    def set_daemon_parameters(self) -> bool:
        """ Set all daemon parameters based on defaults in env.UT_CONST and the config.py file.

        :return:  True on success
        """
        read_status = True
        if not env.UT_CONST.ups_config_ini:
            return False
        config = configparser.ConfigParser()
        try:
            config.read(env.UT_CONST.ups_config_ini)
        except configparser.Error as err:
            LOGGER.exception('config parser error: %s', err)
            print('Error in ups-utils.ini file.  Using defaults')
            return True
        LOGGER.debug('config[DaemonPaths]: %s', dict(config['DaemonPaths']))
        LOGGER.debug('config[DaemonScripts]: %s', dict(config['DaemonScripts']))
        LOGGER.debug('config[DaemonParameters]: %s', dict(config['DaemonParameters']))
        self.daemon_params['ups_ini_file'] = env.UT_CONST.ups_config_ini

        # Set path definitions
        for path_name in self.daemon_paths:
            if isinstance(config['DaemonPaths'][path_name], str):
                self.daemon_params[path_name] = os.path.expanduser(config['DaemonPaths'][path_name])
                if self.daemon_params[path_name]:
                    if not os.path.isdir(self.daemon_params[path_name]):
                        print('Missing directory for {} path_name: {}'.format(path_name, self.daemon_params[path_name]))
                        read_status = False
        if self.daemon_params['boinc_home']:
            os.environ['BOINC_HOME'] = self.daemon_params['boinc_home']

        # Set script definitions
        for script_name in self.daemon_scripts:
            if isinstance(config['DaemonScripts'][script_name], str):
                self.daemon_params[script_name] = os.path.join(self.daemon_params['ups_utils_script_path'],
                                                               config['DaemonScripts'][script_name])
                if self.daemon_params[script_name]:
                    if not os.path.isfile(self.daemon_params[script_name]):
                        print('Missing {} script: {}'.format(script_name, self.daemon_params[script_name]))
                        read_status = False

        # Set script parameters
        for parameter_name in self.daemon_param_names:
            if re.search(env.UT_CONST.PATTERNS['INI'], config['DaemonParameters'][parameter_name]):
                raw_param = re.sub(r'\s+', '', config['DaemonParameters'][parameter_name])
                params = tuple(int(x) for x in raw_param[1:-1].split(','))
                if parameter_name == 'read_interval':
                    self.daemon_params[parameter_name]['monitor'] = params[0]
                    self.daemon_params[parameter_name]['daemon'] = params[1]
                else:
                    self.daemon_params[parameter_name]['crit'] = params[0]
                    self.daemon_params[parameter_name]['warn'] = params[1]
            else:
                LOGGER.debug('Incorrect format for %s parameter: %s',
                             parameter_name, config['DaemonParameters'][parameter_name])
                print('Incorrect format for {} parameter: {}'.format(
                    parameter_name, config['DaemonParameters'][parameter_name]))
                print('Using default value: {}'.format(self.daemon_params[parameter_name]))

        # Check Daemon Parameter Values
        for parameter_name in self.daemon_param_names:
            if parameter_name == 'read_interval':
                for sub_parameter_name in ['monitor', 'daemon']:
                    if self.daemon_params[parameter_name][sub_parameter_name] < \
                            self.daemon_params[parameter_name]['limit']:
                        env.UT_CONST.log_print('Warning invalid {}-{} value [{}], using defaults'.format(
                                               parameter_name, sub_parameter_name,
                                               self.daemon_params[parameter_name][sub_parameter_name]))
                        self.daemon_params[parameter_name] = self.daemon_param_defaults[parameter_name].copy()
            else:
                reset = False
                if self.daemon_param_defaults[parameter_name]['crit'] > \
                        self.daemon_param_defaults[parameter_name]['warn']:
                    if self.daemon_params[parameter_name]['crit'] <= self.daemon_params[parameter_name]['warn']:
                        reset = True
                        env.UT_CONST.log_print('Warning crit must be > warn value, '
                                               'using defaults for {}'.format(parameter_name))
                    if self.daemon_params[parameter_name]['crit'] < self.daemon_params[parameter_name]['limit']:
                        reset = True
                        env.UT_CONST.log_print('Warning crit must be >= limit value, '
                                               'using defaults for {}'.format(parameter_name))
                    if self.daemon_params[parameter_name]['warn'] < self.daemon_params[parameter_name]['limit']:
                        reset = True
                        env.UT_CONST.log_print('Warning warn must be >= limit value, '
                                               'using defaults for {}'.format(parameter_name))
                else:
                    if self.daemon_params[parameter_name]['crit'] >= self.daemon_params[parameter_name]['warn']:
                        reset = True
                        env.UT_CONST.log_print('Warning crit must be < warn value, '
                                               'using defaults for {}'.format(parameter_name))
                    if self.daemon_params[parameter_name]['crit'] < self.daemon_params[parameter_name]['limit']:
                        reset = True
                        env.UT_CONST.log_print('Warning crit must be >= limit value, '
                                               'using defaults for {}'.format(parameter_name))
                    if self.daemon_params[parameter_name]['warn'] < self.daemon_params[parameter_name]['limit']:
                        reset = True
                        env.UT_CONST.log_print('Warning warn must be >= limit value, '
                                               'using defaults for {}'.format(parameter_name))
                if reset:
                    self.daemon_params[parameter_name] = self.daemon_param_defaults[parameter_name].copy()
        return read_status

    def print_daemon_parameters(self) -> None:
        """ Print all daemon parameters.

        :return:  None
        """
        print('Daemon parameters:')
        for param_name, param_value in self.daemon_params.items():
            print('    {}: {}'.format(param_name, param_value))

    def execute_script(self, script_name: str) -> bool:
        """ Execute script defined in the daemon parameters

        :param: script_name: name of script to be executed
        :return:  True on success
        """
        if script_name not in self.daemon_scripts:
            raise AttributeError('Error: {} no valid script name: [{}]'.format(script_name, self.daemon_scripts))
        if not self.daemon_params[script_name]:
            print('No {} defined'.format(script_name))
            return False
        try:
            cmd = subprocess.Popen(shlex.split(self.daemon_params[script_name]),
                                   shell=False, stdout=subprocess.PIPE)
            while True:
                if cmd.poll() is not None:
                    break
                time.sleep(0.2)
            if cmd.returncode:
                env.UT_CONST.log_print('{} failed with return code: [{}]'.format(script_name, cmd.returncode))
                return False
        except subprocess.CalledProcessError as err:
            print('Error [{}]: could not execute script: {}'.format(err,
                  self.daemon_params[script_name]), file=sys.stderr)
            return False
        return True


def about() -> None:
    """ Display details about this module.

    :return:  None
    """
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
