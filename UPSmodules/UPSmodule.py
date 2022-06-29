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
__author__ = "RicksLab"
__copyright__ = "Copyright (C) 2019 RicksLab"
__credits__ = ['Natalya Langford - Configuration Parser']
__license__ = "GNU General Public License"
__program_name__ = "ups-utils"
__maintainer__ = "RicksLab"
__docformat__ = 'reStructuredText'
# pylint: disable=multiple-statements
# pylint: disable=line-too-long
# pylint: disable=bad-continuation

import os
import sys
import re
import shlex
import shutil
import time
from datetime import datetime
import json
import subprocess
import logging
import pprint
import configparser
from enum import Enum
from typing import Tuple, List, Union, Dict, Generator, Set, Optional
from uuid import uuid4
from UPSmodules import env


LOGGER = logging.getLogger('ups-utils')


class UpsEnum(Enum):
    """ Replace __str__ method of Enum so that name excludes type and can be used as key in other dicts.
    """
    def __str__(self) -> str:
        return self.name

    @classmethod
    def list(cls) -> List[str]:
        """ Return a list of name from current UpsEnum object """
        return list(map(lambda c: c.name, cls))


class ObjDict(dict):
    """ Allow access of dictionary keys by key name.
    """
    # pylint: disable=attribute-defined-outside-init
    # pylint: disable=too-many-instance-attributes
    def __getattr__(self, name) -> str:
        if name in self:
            return self[name]
        raise AttributeError('No such attribute: {}'.format(name))

    def __setattr__(self, name, value) -> None:
        self[name] = value

    def __delattr__(self, name) -> None:
        if name in self:
            del self[name]
        else:
            raise AttributeError('No such attribute: {}'.format(name))


class UpsItem:
    """ Object to represent a UPS """
    _json_keys: Set[str] = {'ups_IP', 'display_name', 'ups_type', 'daemon',
                            'snmp_community', 'uuid', 'ups_model', 'ups_nmc_model'}
    UPS_type: UpsEnum = UpsEnum('type', 'all apc_ap96xx eaton_pw')

    param_labels: Dict[str, str] = {
        'display_name': 'UPS Name',
        'ups_IP': 'UPS IP/FQDN',
        'ups_type': 'UPS Type',
        'mib_ups_model': 'UPS Model',
        'ups_nmc_model': 'NMC Model',
        'sep1':                '#',
        'valid': 'Valid',
        'compatible': 'Compatible',
        'accessible': 'Accessible',
        'responsive': 'Responsive',
        'daemon': 'Daemon',
        'sep2':                '#',
        'mib_ups_name': 'UPS Real Name',
        'mib_ups_info': 'General UPS Information',
        'mib_bios_serial_number': 'UPS BIOS Serial Number',
        'mib_firmware_revision': 'UPS Firmware Revision',
        'mib_ups_manufacture_date': 'UPS Manufacture Date',
        'mib_ups_type': 'UPS Model Type',
        'mib_ups_contact': 'UPS Contact',
        'mib_ups_location': 'UPS Location',
        'mib_comms': 'Communicating with UPS Device',
        'sep3':                '#',
        'mib_system_status': 'UPS System Status',
        'mib_battery_status': 'Battery Status',
        'mib_battery_replace': 'Battery Replacement',
        'mib_last_self_test_result': 'Last Self Test Results',
        'mib_last_self_test_date': 'Date of Last Self Test',
        'mib_ups_uptime': 'UPS Up Time',
        'mib_reason_for_last_transfer': 'Last Transfer Event',
        'mib_battery_temperature': 'Battery Temp (C)',
        'mib_ups_env_temp': 'UPS Environment Temp (C)',
        'sep4':                '#',
        'mib_battery_capacity': 'Percentage of Total Capacity',
        'mib_time_on_battery': 'Time on Battery (min)',
        'mib_battery_runtime_remain': 'Runtime Remaining (min)',
        'sep5':                '#',
        'mib_input_voltage': 'Input Voltage (V)',
        'mib_input_frequency': 'Input Frequency (Hz)',
        'sep6':                '#',
        'mib_output_voltage': 'Output Voltage (V)',
        'mib_output_frequency': 'Output Frequency (Hz)',
        'mib_output_load': 'Output Load as % of Capacity',
        'mib_output_power': 'Output Power (W)',
        'mib_output_current': 'Output Current (A)'}

    ordered_table_items: Tuple[str, ...] = (
        'display_name', 'mib_ups_name', 'ups_IP', 'mib_ups_model', 'ups_type', 'ups_nmc_model', 'mib_ups_location',
        'daemon', 'mib_ups_env_temp', 'mib_input_voltage', 'mib_input_frequency', 'mib_output_voltage',
        'mib_output_frequency', 'mib_output_current', 'mib_output_power', 'mib_output_load',
        'mib_battery_capacity', 'mib_time_on_battery', 'mib_battery_runtime_remain', 'mib_system_status',
        'mib_battery_status')
    _short_list: Set[str] = {'ups_IP', 'display_name', 'mib_ups_model', 'responsive', 'daemon'}
    table_list: Set[str] = {'display_name', 'ups_IP', 'ups_type', 'mib_ups_model', 'ups_nmc_model', 'daemon'}
    mark_up_codes = env.UT_CONST.mark_up_codes
    TXT_style: UpsEnum = UpsEnum('style', 'warn crit green bold normal daemon')

    def __init__(self, json_details: dict):
        # UPS list from ups-config.json for monitor and ls utils.
        self.skip_list: List[str] = []
        self.prm: ObjDict = ObjDict({
            'uuid': None,
            'ups_IP': None,
            'display_name': None,
            'ups_type': None,
            'ups_model': None,
            'ups_nmc_model': None,
            'snmp_community': None,
            'daemon': False,
            'valid': False,
            'compatible': False,
            'accessible': False,
            'responsive': False})
        for cmd in UpsComm.all_mib_cmd_names[UpsComm.MIB_group.all]:
            self.prm.update({cmd: None})

        self.initialize_cls_table_list()
        # Load initial data from json dict.
        for item_name, item_value in json_details.items():
            if item_name not in self._json_keys:
                LOGGER.debug('%s: Invalid key [%s] ignored', env.UT_CONST.ups_json_file, item_name)
                continue
            if item_name == 'ups_type':
                if re.search(env.UT_CONST.PATTERNS['APC96'], item_value): item_value = 'apc_ap96xx'
                if item_value in UpsComm.MIB_nmc.list():
                    self.prm['valid'] = True
                    self.prm['compatible'] = True
                    self.prm[item_name] = UpsComm.MIB_nmc[item_value]
                else:
                    env.UT_CONST.process_message('Invalid ups_type [{}] from [{}]'.format(
                        item_name, env.UT_CONST.ups_json_file))
                    self.prm['valid'] = False
                    self.prm['compatible'] = False
                    self.prm[item_name] = UpsComm.MIB_nmc['none']
            else:
                self.prm[item_name] = item_value

        if self.prm['ups_type'] in UpsComm.MIB_nmc.list():
            self.prm['compatible'] = True

        # Check accessibility
        self.ups_comm: UpsComm = UpsComm(self)
        if self.ups_comm.is_valid_ip_fqdn(self.prm['ups_IP']):
            self.prm['valid'] = self.prm['valid'] and True
        if self.ups_comm.check_ip_access(self.prm['ups_IP']):
            self.prm['accessible'] = True
        if self.ups_comm.check_snmp_response(self):
            self.prm['responsive'] = True

        mib_cmd_group = UpsComm.MIB_nmc.apc_ap96xx \
            if re.search(env.UT_CONST.PATTERNS['APC'], self.prm['ups_type'].name) \
            else UpsComm.MIB_nmc.eaton_pw
        self.prm['mib_commands'] = self.ups_comm.all_mib_cmds[mib_cmd_group]
        self.daemon = None

    @classmethod
    def initialize_cls_table_list(cls) -> None:
        """ Initialize the class data table_list.
        """
        cls.table_list = cls.table_list.union(UpsComm.all_mib_cmd_names[UpsComm.MIB_group.monitor])

    def __getitem__(self, param_name: str) -> any:
        try:
            return self.prm[param_name]
        except KeyError as error:
            raise KeyError('KeyError: invalid param_name: {}'.format(param_name)) from error

    def __setitem__(self, param_name: str, value: any) -> None:
        self.prm[param_name] = value

    def __repr__(self) -> str:
        return '{} - {} - {}'.format(self['uuid'], self['display_name'], self['ups_IP'])

    def __str__(self) -> str:
        return re.sub(r'\'', '\"', pprint.pformat(self.prm, indent=2, width=120))

    def mib_command_names(self, cmd_group: Optional[UpsEnum] = None) -> Generator[str, None, None]:
        """ Returns mib command names for the given command group.

        :param cmd_group: Specifies the group of MIB commands.  Default is all.
        :return: Generator yielding mib command names
        """
        if not cmd_group:
            cmd_group = UpsComm.MIB_group.all
        if cmd_group == UpsComm.MIB_group.all:
            if self.prm.ups_type == UpsComm.MIB_nmc.apc_ap96xx:
                cmd_group = UpsComm.MIB_group.all_apc
            else:
                cmd_group = UpsComm.MIB_group.all_eaton
        for cmd_name in self.ups_comm.mib_commands:
            if cmd_name in UpsComm.all_mib_cmd_names[cmd_group]:
                yield cmd_name

    def get_ups_parameter_value(self, param_name: str) -> Union[str, None]:
        """ Get ups parameter value for parameter name from target UPS or active UPS if not specified

        :param param_name: Target parameter name
        :return: Parameter value as string else None
        """
        return self.prm[param_name] if param_name in self.prm.keys() else None

    def ups_uuid(self) -> str:
        """ Get the uuid value for the target UPS or active UPS if target is None.

        :return:  The uuid as a int.
        """
        return self.prm['uuid']

    def ups_name(self) -> str:
        """ Get the name value for the target UPS or active UPS if target is None.

        :return:  The name as a str.
        """
        return self.prm['display_name']

    def ups_type(self) -> UpsEnum:
        """ Get the type value for the target UPS or active UPS if target is None.

        :return:  The ups_type as a UpsEnum.
        """
        return self.prm['ups_type']

    def ups_ip(self) -> None:
        """ Get the IP address value for the target UPS or active UPS if target is None.

        :return:  The IP address as a str.
        """
        return self.prm['ups_IP']

    def is_compatible(self):
        """ Return flag indicating compatibility """
        return self.prm.compatible

    def is_accessible(self):
        """ Return flag indicating accessibility """
        return self.prm.accessible

    def is_responsive(self):
        """ Return flag indicating ability to respond to ping """
        return self.prm.responsive

    def send_snmp_command(self, cmd_name: str, display: bool = True) -> str:
        """ Send the given command to UPS using UpsComm object """
        return self.ups_comm.send_snmp_command(cmd_name, self, display)

    def read_ups_list_items(self, cmd_group: UpsEnum, display: bool = False) -> bool:
        """ Read data for a group of commands from UpsComm object """
        return self.ups_comm.read_ups_list_items(cmd_group, self, display=display)

    def print_snmp_commands(self) -> None:
        """ Print all mib command details for this UPS """
        print('{}\n{} - {} - {}\n{}'.format('#'.ljust(50, '#'), self.prm.display_name, self.prm.mib_ups_name,
                                            self.prm.ups_nmc_model, '#'.ljust(50, '#')))
        self.ups_comm.print_snmp_commands()

    def print(self, short: bool = False, input_arg: bool = False, output_arg: bool = False,
              newline: bool = True) -> None:
        """ Display ls like listing function for UPS parameters.

        :param short:  Display short listing
        :param input_arg:  Display input parameters
        :param output_arg:  Display output parameters
        :param newline:  Display terminating newline if True
        """
        if short:
            show_list = self._short_list
        else:
            show_list: Set[str] = UpsComm.all_mib_cmd_names[UpsComm.MIB_group.all].union(self.table_list)
        if input_arg: show_list = show_list.union(UpsComm.all_mib_cmd_names[UpsComm.MIB_group.input])
        if output_arg: show_list = show_list.union(UpsComm.all_mib_cmd_names[UpsComm.MIB_group.output])

        for param_name, param_label in self.param_labels.items():
            if param_name not in show_list: continue
            color = self.mark_up_codes['none']
            color_reset = self.mark_up_codes['none'] if env.UT_CONST.no_markup else self.mark_up_codes['reset']
            pre = '' if param_name == 'display_name' else '   '
            if re.search(r'^sep\d', param_name):
                print('{}{}'.format(pre, param_label.ljust(50, param_label)))
                continue
            if not env.UT_CONST.no_markup: color = self.mark_up_codes['data']
            if param_name == 'mib_ups_info':
                text = env.UT_CONST.wrap(self.prm[param_name], indent=len(param_label)+len(pre)+1)
            else:
                text = self.prm[param_name]
            print('{}{}: {}{}{}'.format(pre, param_label, color, text, color_reset))
        if newline: print('')


class UpsDaemon:
    """ Define a Daemon configuration object """
    # Configuration details
    _daemon_paths: Tuple[str, ...] = ('boinc_home', 'ups_utils_script_path')
    _daemon_scripts: Tuple[str, ...] = ('suspend_script', 'resume_script', 'shutdown_script', 'cancel_shutdown_script')
    _daemon_param_names: Tuple[str, ...] = ('read_interval', 'threshold_env_temp', 'threshold_battery_time_rem',
                                            'threshold_time_on_battery', 'threshold_battery_load',
                                            'threshold_battery_capacity')
    daemon_items_dict: Dict[str, tuple] = {
        'DaemonPaths': _daemon_paths,
        'DaemonScripts': _daemon_scripts,
        'DaemonParameters': _daemon_param_names}
    config_name_list: List[str] = ['DaemonPaths', 'DaemonScripts', 'DaemonParameters']

    daemon_param_defaults: Dict[str, Union[str, Dict[str, int]]] = {
        'ups_utils_script_path': os.path.expanduser('~/.local/bin/'),
        # Low limit
        'read_interval': {'monitor': 10, 'daemon': 30, 'limit': 10, 'limit_type': 'low'},
        'threshold_battery_time_rem': {'crit': 5, 'warn': 10, 'limit': 4, 'limit_type': 'low'},
        'threshold_battery_capacity': {'crit': 10, 'warn': 50, 'limit': 5, 'limit_type': 'low'},
        # High limit
        'threshold_env_temp': {'crit': 35, 'warn': 30, 'limit': 35, 'limit_type': 'high'},
        'threshold_battery_load': {'crit': 90, 'warn': 80, 'limit': 95, 'limit_type': 'high'},
        'threshold_time_on_battery': {'crit': 5, 'warn': 3, 'limit': 90, 'limit_type': 'high'},
    }
    daemon_param_dict: Dict[str, str] = {
        'mib_ups_env_temp': 'threshold_env_temp',
        'mib_time_on_battery': 'threshold_time_on_battery',
        'mib_battery_runtime_remain': 'threshold_battery_time_rem',
        'mib_output_load': 'threshold_battery_load',
        'mib_battery_capacity': 'threshold_battery_capacity'}

    # Set params to defaults
    daemon_params: Dict[str, Union[str, dict, None]] = {
        'boinc_home': None, 'ups_utils_script_path': daemon_param_defaults['ups_utils_script_path'],
        'suspend_script': None, 'resume_script': None,
        'shutdown_script': None, 'cancel_shutdown_script': None,
        'read_interval': daemon_param_defaults['read_interval'].copy(),
        'threshold_env_temp': daemon_param_defaults['threshold_env_temp'].copy(),
        'threshold_battery_time_rem': daemon_param_defaults['threshold_battery_time_rem'].copy(),
        'threshold_time_on_battery': daemon_param_defaults['threshold_time_on_battery'].copy(),
        'threshold_battery_load': daemon_param_defaults['threshold_battery_load'].copy(),
        'threshold_battery_capacity': daemon_param_defaults['threshold_battery_capacity'].copy()}

    def __init__(self):
        self.config: Union[dict, None] = None
        self.daemon_ups: Union[UpsItem, None] = None
        self.daemon_params: Dict[str, Dict[str, Union[str, int]]]

        if self.read_daemon_config():
            self.set_daemon_parameters()

    def __str__(self) -> str:
        return re.sub(r'\'', '\"', pprint.pformat(self.daemon_params, indent=2, width=120))

    def daemon_format(self, command_name: str, value: Union[int, float, str],
                      gui_text_style: bool = False) -> Union[str, None, UpsEnum]:
        """

        :param command_name:
        :param value:
        :param gui_text_style:
        :return:
        """
        if command_name not in self.daemon_param_dict:
            return UpsItem.TXT_style.bold if gui_text_style else 'none'
        if value in {None, 'none', '', '---'}:
            return UpsItem.TXT_style.normal if gui_text_style else 'none'
        if isinstance(value, str):
            if value.isnumeric():
                value = int(value)
            else:
                return UpsItem.TXT_style.bold if gui_text_style else 'none'

        limits = self.daemon_params[self.daemon_param_dict[command_name]]
        if limits['limit_type'] == 'high':
            if value >= limits['crit']:
                return UpsItem.TXT_style.crit if gui_text_style else 'crit'
            elif value >= limits['warn']:
                return UpsItem.TXT_style.warn if gui_text_style else 'warn'
        else:
            if value <= limits['crit']:
                return UpsItem.TXT_style.crit if gui_text_style else 'crit'
            elif value <= limits['warn']:
                return UpsItem.TXT_style.warn if gui_text_style else 'warn'
        return UpsItem.TXT_style.bold if gui_text_style else 'none'

    def read_daemon_config(self) -> bool:
        """ Read the daemon config file.

        :return:  True on success.
        """
        if not env.UT_CONST.ups_config_ini:
            print('Error ups-utils.ini filename not set.')
            return False

        self.config = configparser.ConfigParser()
        try:
            self.config.read(env.UT_CONST.ups_config_ini)
        except configparser.MissingSectionHeaderError as err:
            LOGGER.debug('config parser error: %s', err)
            print('Error: Data without section header in ups-utils.ini file.')
            return False
        except configparser.Error as err:
            LOGGER.debug('config parser error: %s', err)
            print('Error: Could not read ups-utils.ini file.')
            return False
        missing_section = False
        for config_name in ('DaemonPaths', 'DaemonScripts', 'DaemonParameters'):
            if config_name not in self.config:
                env.UT_CONST.process_message('Error reading [{}], missing [{}] section.'.format(
                    env.UT_CONST.ups_config_ini, config_name))
                missing_section = True
        if missing_section:
            env.UT_CONST.process_message('       Using defaults.')
            return False
        LOGGER.debug('config[DaemonPaths]: %s', dict(self.config['DaemonPaths']))
        LOGGER.debug('config[DaemonScripts]: %s', dict(self.config['DaemonScripts']))
        LOGGER.debug('config[DaemonParameters]: %s', dict(self.config['DaemonParameters']))
        return True

    def set_daemon_parameters(self) -> bool:
        """ Set all daemon parameters based on defaults in env.UT_CONST and the config.py file.

        :return:  True on success
        """
        read_status = True

        def param_error(c_name: str, c_item: str) -> None:
            """ Output standard error messages on issue with reading config file.

            :param c_name:  Top level config names.
            :param c_item: Name of second level item.
            """
            env.UT_CONST.process_message('Config [{}] item [{}] missing in [{}]'.format(
                c_name, c_item, env.UT_CONST.ups_config_ini))
            env.UT_CONST.process_message('Setting to default')

        def param_check_set(c_name: str, c_item: str, c_value: str) -> bool:
            """ Checks daemon values from config and sets if pass.

            :param c_name:
            :param c_item:
            :param c_value:
            :return: True if everything QX
            """
            if c_name == 'DaemonPaths':
                self.daemon_params[c_item] = os.path.expanduser(c_value)
                if self.daemon_params[c_item]:
                    if not os.path.isdir(self.daemon_params[c_item]):
                        self.daemon_params[c_item] = None
                        env.UT_CONST.process_message('Config [{}] item [{}] invalid file/path [{}]'.format(
                            c_name, c_item, c_value))
                        return False
            elif c_name == 'DaemonScripts':
                if not self.daemon_params['ups_utils_script_path']:
                    self.daemon_params[c_item] = None
                    env.UT_CONST.process_message('Config [{}] item [{}] invalid file/path [{}]'.format(
                        c_name, c_item, c_value))
                    return False
                self.daemon_params[c_item] = os.path.join(self.daemon_params['ups_utils_script_path'], c_value)
                if not os.path.isfile(self.daemon_params[c_item]):
                    self.daemon_params[c_item] = None
                    env.UT_CONST.process_message('Config [{}] item [{}] invalid file/path [{}]'.format(
                        c_name, c_item, c_value))
            elif c_name == 'DaemonParameters':
                if re.search(env.UT_CONST.PATTERNS['INI'], c_value):
                    params = (0, 0)
                    if isinstance(c_value, str):
                        raw_param = re.sub(r'\s+', '', c_value)
                        params = tuple(int(x) for x in raw_param[1:-1].split(','))
                    try:
                        if c_item == 'read_interval':
                            self.daemon_params[c_item]['monitor'] = params[0]
                            self.daemon_params[c_item]['daemon'] = params[1]
                        else:
                            self.daemon_params[c_item]['crit'] = params[0]
                            self.daemon_params[c_item]['warn'] = params[1]
                    except KeyError:
                        env.UT_CONST.process_message('Config [{}] item [{}] invalid value [{}]'.format(
                            c_name, c_item, c_value))
            return True

        # Sets all daemon parameter items.  Any unexpected items are skipped.
        for config_name in self.config_name_list:
            config_items = self.daemon_items_dict[config_name]
            for config_item_name in config_items:
                if config_item_name in self.config[config_name]:
                    config_item_value = self.config[config_name][config_item_name]
                    if isinstance(config_item_value, str):
                        param_check_set(config_name, config_item_name, config_item_value)
                    else: param_error(config_name, config_item_name)
                else: param_error(config_name, config_item_name)

        if self.daemon_params['boinc_home']:
            os.environ['BOINC_HOME'] = self.daemon_params['boinc_home']

        # Check Daemon Parameter Values
        for parameter_name in self._daemon_param_names:
            if parameter_name == 'read_interval':
                for sub_parameter_name in {'monitor', 'daemon'}:
                    if self.daemon_params[parameter_name][sub_parameter_name] < \
                            self.daemon_params[parameter_name]['limit']:
                        env.UT_CONST.process_message('Warning invalid {}-{} value [{}], using defaults'.format(
                                               parameter_name, sub_parameter_name,
                                               self.daemon_params[parameter_name][sub_parameter_name]), verbose=True)
                        self.daemon_params[parameter_name] = self.daemon_param_defaults[parameter_name].copy()
            else:
                reset = False
                if self.daemon_param_defaults[parameter_name]['limit_type'] == 'high':
                    if self.daemon_params[parameter_name]['crit'] <= self.daemon_params[parameter_name]['warn']:
                        reset = True
                        env.UT_CONST.process_message('Warning: crit {} NOT > warn {}, using defaults for {}'.format(
                            self.daemon_params[parameter_name]['crit'], self.daemon_params[parameter_name]['warn'],
                            parameter_name), verbose=True)
                    if self.daemon_params[parameter_name]['crit'] > self.daemon_params[parameter_name]['limit']:
                        reset = True
                        env.UT_CONST.process_message('Warning: crit {} NOT <= limit {}, using defaults for {}'.format(
                            self.daemon_params[parameter_name]['crit'], self.daemon_params[parameter_name]['limit'],
                            parameter_name), verbose=True)
                else:
                    if self.daemon_params[parameter_name]['crit'] >= self.daemon_params[parameter_name]['warn']:
                        reset = True
                        env.UT_CONST.process_message('Warning: crit {} NOT < warn {}, using defaults for {}'.format(
                            self.daemon_params[parameter_name]['crit'], self.daemon_params[parameter_name]['warn'],
                            parameter_name), verbose=True)
                    if self.daemon_params[parameter_name]['crit'] < self.daemon_params[parameter_name]['limit']:
                        reset = True
                        env.UT_CONST.process_message('Warning: crit {} NOT >= limit {}, using defaults for {}'.format(
                            self.daemon_params[parameter_name]['crit'], self.daemon_params[parameter_name]['limit'],
                            parameter_name), verbose=True)
                if reset:
                    self.daemon_params[parameter_name] = self.daemon_param_defaults[parameter_name].copy()
                    print('Defaults: {}: crit = {}, warn = {}, limit = {}'.format(parameter_name,
                          self.daemon_params[parameter_name]['crit'], self.daemon_params[parameter_name]['warn'],
                          self.daemon_params[parameter_name]['limit']))
        return read_status

    @classmethod
    def print_daemon_parameters(cls) -> None:
        """ Print all daemon parameters.
        """
        if env.UT_CONST.no_markup:
            color = reset = ''
        else:
            color = env.UT_CONST.mark_up_codes['data']
            reset = env.UT_CONST.mark_up_codes['reset']
        print('Daemon parameters:')
        for param_name, param_value in cls.daemon_params.items():
            print('    {}: {}{}{}'.format(param_name, color, param_value, reset))
        print('')

    def execute_script(self, script_name: str) -> Tuple[int, str]:
        """ Execute script defined in the daemon parameters

        :param: script_name: name of script to be executed
        :return:  True on success
        """
        if script_name not in self._daemon_scripts:
            raise AttributeError('Error: {} no valid script name: [{}]'.format(script_name, self._daemon_scripts))
        if not self.daemon_params[script_name]:
            message = 'No {} defined'.format(script_name)
            env.UT_CONST.process_message('No {} defined'.format(script_name))
            return -1, message
        try:
            cmd = subprocess.Popen(shlex.split(self.daemon_params[script_name]),
                                   shell=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            while True:
                if cmd.poll() is not None:
                    break
                time.sleep(0.1)
            message = cmd.communicate()[0].decode("utf-8")
            LOGGER.debug(message)
            if cmd.returncode:
                env.UT_CONST.process_message('{} failed with return code: [{}]'.format(script_name, cmd.returncode),
                                             verbose=True)
            return cmd.returncode, message
        except subprocess.CalledProcessError as err:
            message = 'Error [{}]: could not execute script: {}'.format(err, self.daemon_params[script_name])
            env.UT_CONST.process_message(message)
            return False, message


class UpsList:
    """ Object to represent a list of UPSs """
    def __init__(self, daemon: bool = True):
        self.update_time: datetime = env.UT_CONST.now()
        self.list: Dict[str, UpsItem] = {}
        self.daemon: Union[UpsDaemon, None] = UpsDaemon() if daemon else None
        if not self.read_ups_json():
            env.UT_CONST.process_message('Fatal: Could not read [{}] file.'.format(env.UT_CONST.config_files['json']))
            sys.exit(-1)
        if self.get_daemon_ups():
            self.get_daemon_ups().daemon = self.daemon

    def read_set_daemon(self) -> None:
        """ Used to refresh the daemon configuration parameters by rereading file.
        """
        self.daemon: Union[UpsDaemon, None] = UpsDaemon()
        self.get_daemon_ups().daemon = self.daemon
        print('daemon refreshed')
        if env.UT_CONST.verbose:
            self.print_daemon_parameters()
        env.UT_CONST.refresh_daemon = False

    def __repr__(self) -> str:
        return re.sub(r'\'', '\"', pprint.pformat(self.list, indent=2, width=120))

    def __str__(self) -> str:
        num_ups = self.num_upss()
        out_str = '{} UPSs listed in {}.\n'.format(num_ups['total'], env.UT_CONST.ups_json_file)
        out_str += '    {} are compatible, {} are accessible, {} are responsive, '\
                   '{} are valid, and {} are daemon.\n'.format(num_ups['compatible'], num_ups['accessible'],
                                                               num_ups['responsive'], num_ups['valid'],
                                                               num_ups['daemon'])
        return out_str

    def __getitem__(self, uuid: str) -> UpsItem:
        if uuid in self.list:
            return self.list[uuid]
        raise KeyError('KeyError: invalid uuid: {}'.format(uuid))

    def __setitem__(self, uuid: str, value: UpsItem) -> None:
        self.list[uuid] = value

    def __iter__(self) -> Generator[UpsItem, None, None]:
        for value in self.list.values():
            yield value

    def items(self) -> Generator[Union[str, UpsItem], None, None]:
        """
        Get uuid, gpu pairs from a UpsList object.

        :return:  uuid, ups pair
        """
        for key, value in self.list.items():
            yield key, value

    def uuids(self) -> Generator[str, None, None]:
        """ Get uuids of the UpsList object.

        :return: uuids from the UpsList object.
        """
        for key in self.list:
            yield key

    def upss(self) -> Generator[UpsItem, None, None]:
        """ Get UpsItems from a GpuList object.

        :return: UpsItem
        """
        return self.__iter__()

    def add(self, ups_item: UpsItem) -> None:
        """ Add given UpsItem to the UpsList.
        """
        self[ups_item.prm.uuid] = ups_item
        LOGGER.debug('Added UPS Item %s to UPS List', ups_item.prm.uuid)

    def print_daemon_parameters(self) -> None:
        """ Print the daemon parameters read from config file. """
        self.daemon.print_daemon_parameters()

    def print(self, short: bool = False, input_arg: bool = False, output_arg: bool = False,
              newline: bool = True) -> None:
        """ Print each UPS item in the UpsList """
        for ups in self.upss():
            ups.print(short, input_arg, output_arg)
        if newline:
            print('')

    def get_daemon_ups(self) -> Union[UpsItem, None]:
        """ Get the ups object for the daemon UPS.

        :return: The daemon ups object or None if none
        """
        for ups in self.list.values():
            if ups.prm.daemon:
                return ups
        return None

    def num_upss(self, ups_type: UpsEnum = UpsItem.UPS_type.all) -> Dict[str, int]:
        """ Return the count of UPSs by total, accessible, compatible, responsive, valid, and daemon.

        :param ups_type: Only count UPSs of specific ups_type or all ups_type by default.
        :return: Dictionary of UPS counts
        """
        try:
            ups_type_name = ups_type.name
        except AttributeError as error:
            raise AttributeError('Error: {} not a valid vendor name: [{}]'.format(ups_type, UpsItem.UPS_type)) from error
        results_dict = {'ups_type': ups_type_name, 'total': 0,
                        'accessible': 0, 'compatible': 0, 'responsive': 0, 'valid': 0, 'daemon': 0}
        for ups in self.upss():
            if ups_type != UpsItem.UPS_type.all:
                if ups_type != ups.prm.ups_type:
                    continue
            if ups.prm.daemon:
                results_dict['daemon'] += 1
            if ups.prm.valid:
                results_dict['valid'] += 1
            if ups.prm.accessible:
                results_dict['accessible'] += 1
            if ups.prm.compatible:
                results_dict['compatible'] += 1
            if ups.prm.responsive:
                results_dict['responsive'] += 1
            results_dict['total'] += 1
        return results_dict

    def read_all_ups_list_items(self, cmd_group: UpsEnum, errups: bool = True, display: bool = False) -> bool:
        """ Get the specified list of monitor mib commands for all UPSs.

        :param cmd_group:  A list of mib commands to be read from the all UPSs.
        :param errups: Flag to indicate if error UPS should be included.
        :param display: Flag to indicate if parameters should be displayed as read.
        :return:  dict of results from the reading of all commands from all UPSs.
        """
        if env.UT_CONST.refresh_daemon:
            self.read_set_daemon()
        for ups in self.upss():
            if not errups:
                if not ups.prm.responsive:
                    continue
            ups.read_ups_list_items(cmd_group, display=display)
        return True

    def read_ups_json(self) -> bool:
        """ Reads the ups-config.json file which contains parameters for UPSs to be used by utility.
            Build of list of UpsItems representing each of the UPSs defined in the json file.

        :return: boolean True if no problems reading list
        """
        if not env.UT_CONST.ups_json_file:
            print('Error: {} file not defined: {}'.format('ups-config.json', env.UT_CONST.config_files['json']))
            return False
        if not os.path.isfile(env.UT_CONST.ups_json_file):
            print('Error: {} file not found: {}'.format(os.path.basename(env.UT_CONST.ups_json_file),
                                                        env.UT_CONST.ups_json_file))
            return False
        try:
            with open(env.UT_CONST.ups_json_file, 'r') as ups_list_file:
                ups_items = json.load(ups_list_file)
        except FileNotFoundError as error:
            env.UT_CONST.process_message("Error: File not found error for [{}]: {}".format(
                env.UT_CONST.ups_json_file, error), verbose=True)
            return False
        except PermissionError as error:
            env.UT_CONST.process_message("Error: File permission error for [{}]: {}".format(
                env.UT_CONST.ups_json_file, error), verbose=True)
            return False
        except json.decoder.JSONDecodeError as error:
            env.UT_CONST.process_message("Error: File format error for [{}]:\n       {}".format(
                env.UT_CONST.ups_json_file, error), verbose=True)
            return False
        for ups_dict in ups_items.values():
            uuid = uuid4().hex
            ups_dict['uuid'] = uuid
            self.list[uuid] = UpsItem(ups_dict)
        return True

    # Methods to get, check, and list UPSs
    def get_name_for_ups_uuid(self, ups_uuid: int) -> Union[str, None]:
        """ Get the ups name for a given uuid

        :param ups_uuid: Universally unique identifier for a UPS
        :return: name of the ups or None if not found
        """
        for ups in self.upss():
            if ups['uuid'] == ups_uuid:
                return ups['display_name']
        return None

    def get_uuid_for_ups_name(self, ups_name: str) -> Union[str, None]:
        """ Get uuid for ups with given name.

        :param ups_name: The target ups name.
        :return: The uuid as str or None if not found
        """
        for ups in self.upss():
            if ups['display_name'] == ups_name:
                return ups['uuid']
        return None

    def get_ups_type_list(self) -> Tuple[UpsEnum]:
        """ Get a tuple of unique ups types.

        :return: A tuple of unique types.
        """
        type_list: List[UpsEnum] = []
        for ups in self.upss():
            if ups.prm.ups_type not in type_list:
                type_list.append(ups.prm.ups_type)
        return tuple(type_list)

    @staticmethod
    def get_mib_commands(cmd_group: UpsEnum) -> Set[str]:
        """ Returns all command mib names of the given group """
        return UpsComm.all_mib_cmd_names[cmd_group]


class UpsComm:
    """ Class definition for UPS communication object."""

    # UPS response bit string decoders
    decoders: Dict[str, Tuple[str, ...]] = {
        'apc_system_status': ('Abnormal', 'OnBattery', 'LowBattery', 'OnLine', 'ReplaceBattery',
                              'SCE', 'AVR_Boost', 'AVR_Trim', 'OverLoad', 'RT_Calibration',
                              'BatteriesDischarged', 'ManualBypass', 'SoftwareBypass', 'Bypass-InternalFault',
                              'Bypass-SupplyFailure', 'Bypass-FanFailure', 'SleepOnTimer', 'SleepNoPower',
                              'On', 'Rebooting', 'BatterCommLost', 'ShutdownInitiated', 'Boost/TrimFailure',
                              'BadOutVoltage', 'BatteryChargerFail', 'HiBatTemp', 'WarnBatTemp', 'CritBatTemp',
                              'SelfTestInProgress', 'LowBat/OnBat', 'ShutdownFromUpstream',
                              'ShutdownFromDownstream', 'NoBatteriesAttached', 'SyncCmdsInProg',
                              'SyncSleepInProg', 'SyncRebootInProg', 'InvDCimbalance', 'TransferReadyFailure',
                              'Shutdown/Unable to Transfer', 'LowBatShutdown', 'FanFail', 'MainRelayFail',
                              'BypassRelayFail', 'TempBypass', 'HighInternalTemp', 'BatTempSensorFault',
                              'InputOORforBypass', 'DCbusOverV', 'PFCfailure', 'CritHWfail', 'Green/ECO mode',
                              'HotStandby', 'EPO', 'LoadAlarmViolation', 'BypassPhaseFault',
                              'UPSinternalComFail', 'EffBoosterMode', 'Off', 'Standby', 'Minor/EnvAlarm')}

    MIB_nmc: UpsEnum = UpsEnum('nmc', 'none all apc_ap96xx eaton_pw')
    all_mib_cmds: Dict[MIB_nmc, Dict[str, Dict[str, Union[str, Dict[str, str], None]]]] = {
        # MiBs for APC UPS with AP96xx NMC
        MIB_nmc.none: {},
        MIB_nmc.apc_ap96xx: {
            'mib_ups_info': {'iso': 'iso.3.6.1.2.1.1.1.0',
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
            'mib_ups_env_temp': {'iso': 'iso.3.6.1.4.1.318.1.1.25.1.2.1.6.1.1',
                                 'name': 'UPS Environment Temp',
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
            'mib_battery_replace': {'iso': 'iso.3.6.1.4.1.318.1.1.1.2.2.4.0',
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
        MIB_nmc.eaton_pw: {
            'mib_ups_info': {'iso': 'iso.3.6.1.2.1.1.1.0',
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

    _valid_type_keys = [x.name for x in all_mib_cmds]
    # UPS MiB Commands lists
    _mib_all_apc_ap96xx: Set[str] = set(all_mib_cmds[MIB_nmc.apc_ap96xx].keys())
    _mib_all_eaton_pw: Set[str] = set(all_mib_cmds[MIB_nmc.eaton_pw].keys())
    _mib_statmon: Set[str] = {'mib_ups_name', 'mib_ups_type', 'mib_ups_location', 'mib_ups_info', 'mib_ups_model'}
    _mib_static: Set[str] = {'mib_ups_name', 'mib_ups_info', 'mib_bios_serial_number', 'mib_firmware_revision',
                             'mib_ups_type', 'mib_ups_location', 'mib_ups_uptime'}
    _mib_dynamic: Set[str] = {'mib_ups_env_temp', 'mib_battery_capacity', 'mib_time_on_battery',
                              'mib_battery_runtime_remain', 'mib_input_voltage', 'mib_input_frequency',
                              'mib_output_voltage', 'mib_output_frequency', 'mib_output_load',
                              'mib_output_current', 'mib_output_power', 'mib_system_status',
                              'mib_battery_status'}
    _mib_output: Set[str] = {'mib_output_voltage', 'mib_output_frequency', 'mib_output_load',
                             'mib_output_current', 'mib_output_power'}
    _mib_input: Set[str] = {'mib_input_voltage', 'mib_input_frequency'}
    MIB_group: UpsEnum = UpsEnum('group', 'all all_apc all_eaton monitor static dynamic input output')
    all_mib_cmd_names: Dict[UpsEnum, Set[str]] = {
        MIB_group.all:       _mib_all_apc_ap96xx,   # I choose all to be apc since eaton is a subset of apc.
        MIB_group.all_apc:   _mib_all_apc_ap96xx,
        MIB_group.all_eaton: _mib_all_eaton_pw,
        MIB_group.monitor:   _mib_dynamic.union(_mib_statmon),
        MIB_group.output:    _mib_output,
        MIB_group.input:     _mib_input,
        MIB_group.static:    _mib_static,
        MIB_group.dynamic:   _mib_dynamic}
    # MIB Command Lists

    # Check if snmp tools are installed
    _snmp_command: str = shutil.which('snmpget')
    if not _snmp_command:
        env.UT_CONST.process_message('Missing dependency: `sudo apt install snmp`', log_flag=True, verbose=True)
        sys.exit(-1)

    def __init__(self, ups_item: UpsItem):
        """
        Initialize mechanism to communicate with UPS via SNMP V2.
        """
        self.snmp_command = self._snmp_command
        self.daemon: bool = ups_item.prm.daemon
        self.ups_type = ups_item.prm['ups_type']
        if ups_item.prm['ups_type'] in self.MIB_nmc.list():
            self.ups_type = ups_item.prm['ups_type'] = self.MIB_nmc[ups_item.prm['ups_type']]
        try:
            self.mib_commands = self.all_mib_cmds[self.ups_type]
        except KeyError:
            print('Invalid entry in [{}].  Value {} not in {}'.format(
                  env.UT_CONST.ups_json_file, ups_item.prm['ups_type'], self._valid_type_keys))
            ups_item.valid = False

    @staticmethod
    def is_valid_ip_fqdn(test_value: str) -> bool:
        """ Check if given string is a valid IP address of FQDN.

        :param test_value: String to be tested.
        :return:  True if valid
        """
        if not re.search(env.UT_CONST.PATTERNS['IPV4'], test_value):
            if not re.search(env.UT_CONST.PATTERNS['FQDN'], test_value):
                if not re.search(env.UT_CONST.PATTERNS['IPV6'], test_value):
                    env.UT_CONST.process_message('ERROR: IP Address entry [{}]'.format(test_value), verbose=True)
                    return False
        return True

    # Set of methods to check if UPS is valid.
    def check_ip_access(self, ip_fqdn: str, validate: bool = False) -> bool:
        """ Check the IP address value for the target UPS or active UPS if target is None.

        :param ip_fqdn:  The target ups dictionary from list or None.
        :param validate:  Validate if legal value provided if True.
        :return:  True if the given IP address is pingable, else False
        """
        if not ip_fqdn: return False
        if validate:
            if not self.is_valid_ip_fqdn(ip_fqdn): return False
        return not bool(os.system('ping -c 1 {} > /dev/null'.format(ip_fqdn)))

    def check_snmp_response(self, ups: UpsItem) -> bool:
        """ Check if the IP address for the target UPS, responds to snmp command.

        :param ups:  The target ups dictionary from list or None.
        :return:  True if the given IP address responds, else False
        """
        cmd_str = '{} -v2c -c {} {} {}'.format(self.snmp_command, ups.prm['snmp_community'],
                                               ups.prm['ups_IP'], 'iso.3.6.1.2.1.1.1.0')

        try:
            snmp_output = subprocess.check_output(shlex.split(cmd_str), shell=False,
                                                  stderr=subprocess.DEVNULL).decode().split('\n')
            LOGGER.debug(snmp_output)
        except subprocess.CalledProcessError as err:
            LOGGER.debug('%s execution error: %s', cmd_str, err)
            return False
        return True

    def read_ups_list_items(self, cmd_group: UpsEnum, ups: UpsItem, display: bool = False) -> bool:
        """ Read the specified list of monitor mib commands for specified UPS.

        :param cmd_group:  A list of mib commands to be read from the specified UPS.
        :param ups:  The target ups item
        :param display: Flag to indicate if parameters should be displayed as read.
        :return:  True on success
        """
        for cmd in UpsComm.all_mib_cmd_names[cmd_group]:
            if cmd in ups.skip_list: continue
            ups.prm[cmd] = self.send_snmp_command(cmd, ups, display=display)
            if ups.prm[cmd] in {None, '', 'none'}:
                ups.skip_list.append(cmd)
                ups.prm[cmd] = '---'
                env.UT_CONST.process_message('UPS {} invalid response: Skipping: {}'.format(
                    ups['display_name'], cmd), verbose=False)
            if cmd == 'mib_ups_info':
                if ups.prm['ups_type'] == UpsComm.MIB_nmc.apc_ap96xx:
                    try:
                        ups.prm['ups_nmc_model'] = re.sub(r'.*MN:', '', ups.prm[cmd]).split()[0]
                        LOGGER.debug('From [%s] got ups_nmc_model of [%s]', ups.prm[cmd], ups.prm['ups_nmc_model'])
                    except(KeyError, IndexError):
                        ups.prm['ups_nmc_model'] = ups.ups_type().name
                else:
                    ups.prm['ups_nmc_model'] = ups.ups_type().name
        # Since PowerWalker NMC is not intended for 110V UPSs, the following correction to output current is needed.
        if ups.prm.ups_type == UpsComm.MIB_nmc.eaton_pw:
            try:
                ups.prm['mib_output_current'] = round((230 / ups.prm['mib_output_voltage']) *
                                                      ups.prm['mib_output_current'], 1)
            except:
                return False
        return True

    def send_snmp_command(self, command_name: str, ups: UpsItem,
                          display: bool = False) -> Union[str, int, float, None]:
        """ Read the specified mib commands results for specified UPS or active UPS if not specified.

        :param command_name:  A command to be read from the target UPS
        :param ups:  The target ups item
        :param display: If true the results will be printed
        :return:  The results from the read, could be str, int or tuple
        """
        if not ups.is_responsive():
            return 'Invalid UPS'
        snmp_mib_commands = ups.prm.mib_commands
        if command_name not in snmp_mib_commands:
            return 'No data'
        cmd_mib = snmp_mib_commands[command_name]['iso']
        cmd_str = '{} -v2c -c {} {} {}'.format(self.snmp_command, ups.prm['snmp_community'],
                                               ups.prm['ups_IP'], cmd_mib)
        try:
            snmp_output = subprocess.check_output(shlex.split(cmd_str), shell=False,
                                                  stderr=subprocess.DEVNULL).decode().split('\n')
        except subprocess.CalledProcessError:
            LOGGER.debug('Error executing snmp %s command [%s] to %s at %s.',
                         command_name, cmd_mib, ups.prm.display_name, ups.ups_ip())
            return None

        value: Union[str, int, float, None] = None

        LOGGER.debug('### command_name: %s', command_name)
        for line in snmp_output:
            if not line: continue
            LOGGER.debug('    Raw data: %s', line)
            if re.match(env.UT_CONST.PATTERNS['SNMP_VALUE'], line):
                value = line.split(':', 1)[1]
                value = re.sub(r'\"', '', value).strip()
        if snmp_mib_commands[command_name]['decode']:
            if value in snmp_mib_commands[command_name]['decode'].keys():
                value = snmp_mib_commands[command_name]['decode'][value]
        if ups.prm['ups_type'] == UpsComm.MIB_nmc.eaton_pw:
            if command_name == 'mib_output_voltage' or command_name == 'mib_output_frequency':
                value = int(value) / 10.0
            elif command_name == 'mib_output_current':
                value = int(value) / 10.0
            elif command_name == 'mib_input_voltage' or command_name == 'mib_input_frequency':
                value = int(value) / 10.0
            elif command_name == 'mib_system_temperature':
                value = int(value) / 10.0
        if command_name == 'mib_system_status' and ups.prm['ups_type'] == UpsComm.MIB_nmc.apc_ap96xx:
            value = self.bit_str_decoder(value, self.decoders['apc_system_status'])
        if command_name == 'mib_time_on_battery' or command_name == 'mib_battery_runtime_remain':
            # Create a minute, string tuple
            if ups.prm['ups_type'] == UpsComm.MIB_nmc.eaton_pw:
                # Process time for eaton_pw
                if command_name == 'mib_time_on_battery':
                    # Measured in seconds.
                    value = int(value)
                else:
                    # Measured in minutes.
                    value = int(value) * 60
                value = round(float(value) / 60.0, 2)
            else:
                # Process time for APC, measured in hundredths of seconds
                value_items = re.sub(r'\(', '', value).split(')')
                value = round(float(value_items[0]) / 100 / 60, 2) if len(value_items) >= 2 else None
        if display:
            if command_name == 'mib_output_current' and ups.prm['ups_type'] == UpsComm.MIB_nmc.eaton_pw:
                print('{}: {} - raw, uncorrected value.'.format(snmp_mib_commands[command_name]['name'], value))
            else:
                print('{}: {}'.format(snmp_mib_commands[command_name]['name'], value))
        LOGGER.debug('    Value: %s', value)
        return value

    @staticmethod
    def bit_str_decoder(value: str, decode_key: tuple) -> str:
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

    def get_mib_commands(self, cmd_group: UpsEnum) -> Set[str]:
        """ Returns all command mib names of the given group """
        return self.all_mib_cmd_names[cmd_group]

    @classmethod
    def print_decoders(cls) -> None:
        """ Prints all bit decoders.
        """
        if env.UT_CONST.no_markup:
            color = reset = ''
        else:
            color = env.UT_CONST.mark_up_codes['data']
            reset = env.UT_CONST.mark_up_codes['reset']
        for decoder_name, decoder_list in cls.decoders.items():
            print('decode key: {}{}{}'.format(color, decoder_name, reset))
            for i, item in enumerate(decoder_list, start=1):
                print('  {:2d}: {}{}{}'.format(i, color, item, reset))
        print('')

    def print_snmp_commands(self) -> None:
        """ Print all supported mib commands for the target UPS, which is the active UPS when not specified.
        """
        if env.UT_CONST.no_markup:
            mib_color = color = reset = ''
        else:
            mib_color = env.UT_CONST.mark_up_codes['green']
            color = env.UT_CONST.mark_up_codes['data']
            reset = env.UT_CONST.mark_up_codes['reset']
        for mib_name, mib_dict in self.mib_commands.items():
            print('{}{}{}:'.format(mib_color, mib_name, reset))
            print('    Value: {}{}{}'.format(color, mib_dict['iso'], reset))
            print('    Description: {}{}{}'.format(color, mib_dict['name'], reset))
            if mib_dict['decode']:
                print('    Decoder:')
                for decoder_name, decoder_list in mib_dict['decode'].items():
                    print('        {}: {}{}{}'.format(decoder_name, color, decoder_list, reset))
        print('')
