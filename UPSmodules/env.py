#!/usr/bin/env python3
"""env.py - Sets environment for ups-utils and establishes global variables.

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
__author__ = 'RicksLab'
__copyright__ = 'Copyright (C) 2019 RicksLab'
__license__ = 'GNU General Public License'
__program_name__ = 'ups-utils'
__maintainer__ = 'RicksLab'
__docformat__ = 'reStructuredText'
# pylint: disable=multiple-statements
# pylint: disable=line-too-long
# pylint: disable=bad-continuation

import argparse
import stat
from platform import release
import sys
import os
import grp
import re
import inspect
import logging
from pathlib import Path
import shutil
from datetime import datetime
from typing import Dict, Union, TextIO, Set
import pytz
from UPSmodules import __version__, __status__, __credits__, __required_pversion__, __required_kversion__

LOGGER = logging.getLogger('ups-utils')


def check_file(filename: str) -> bool:
    """ Check if file is readable.

    :param filename:  Name of file to be checked
    :return: True if ok
    """
    reset = UtConst.mark_up_codes['reset']
    color = '{}{}'.format(UtConst.mark_up_codes['red'],
                          UtConst.mark_up_codes['bold'])
    try:
        with open(filename, 'r') as _file_ptr:
            pass
    except PermissionError as error:
        UtConst.process_message('Error: {}Permission error for [{}]: {}{}'.format(
            color, filename, error, reset), verbose=True)
        return False
    except FileNotFoundError as error:
        UtConst.process_message('Error: {}File not found error for [{}]: {}{}'.format(
            color, filename, error, reset), verbose=True)
        return False
    file_st = os.stat(filename)
    file_grp = grp.getgrgid(file_st.st_gid).gr_name
    file_mode = oct(file_st.st_mode)
    # LOGGER is not enabled yet, so this does not have an effect.
    LOGGER.debug('%s: %s %s', filename, file_grp, file_st)
    if bool(file_st.st_mode & stat.S_IRWXO):
        UtConst.process_message('Error: {}World readable not allowed for:\n'
                                '     [{}]: gid: {} permissions: {}{}'.format(
                                 color, filename, file_grp, file_mode, reset), verbose=True)
        return False
    if file_grp != 'upsutils' and bool(file_st.st_mode & stat.S_IRWXG):
        UtConst.process_message('Error: {}Group readable when group not set to \'upsutils\' is not allowed for:\n'
                                '     [{}]: gid: {} permissions: {}{}'.format(
                                 color, filename, file_grp, file_mode, reset), verbose=True)
        return False
    return True


class UtConst:
    """ Class definition for UPS Utils environment"""
    # FQDN regex credit: https://stackoverflow.com/questions/2532053/validate-a-hostname-string
    # IPV6 regex credit: https://gist.github.com/syzdek/6086792
    PATTERNS = {'HEXRGB': re.compile(r'^#[\da-fA-F]{6}'),
                'SNMP_VALUE': re.compile(r'.*=.*:.*'),
                'IPV4': re.compile(r'^(\d{1,3})(.\d{1,3}){3}$'),
                'IPV6': re.compile(r'^(([\da-fA-F]{1,4}:){7}[\da-fA-F]{1,4}|([\da-fA-F]{1,4}:){1,7}:|'
                                   r'([\da-fA-F]{1,4}:){1,6}:[\da-fA-F]{1,4}|([\da-fA-F]{1,4}:){1,5}'
                                   r'(:[\da-fA-F]{1,4}){1,2}|([\da-fA-F]{1,4}:){1,4}(:[\da-fA-F]{1,4}){1,3}|'
                                   r'([\da-fA-F]{1,4}:){1,3}(:[\da-fA-F]{1,4}){1,4}|([\da-fA-F]{1,4}:){1,2}'
                                   r'(:[\da-fA-F]{1,4}){1,5}|[\da-fA-F]{1,4}:((:[\da-fA-F]{1,4}){1,6})|'
                                   r':((:[\da-fA-F]{1,4}){1,7}|:)|fe80:(:[\da-fA-F]{0,4}){0,4}%[\da-zA-Z]+|'
                                   r'::(ffff(:0{1,4})?:)?((25[0-5]|(2[0-4]|1?\d)?}\d)\.){3}'
                                   r'(25[0-5]|(2[0-4]|1?\d)?\d)|([\da-fA-F]{1,4}:){1,4}:((25[0-5]|'
                                   r'(2[0-4]|1?\d)?\d)\.){3}(25[0-5]|(2[0-4]|1?\d)'
                                   r'?\d))$'),
                'FQDN': re.compile(r'^[a-z\d]([a-z\d-]{0,61}[a-z\d])?(.[a-z\d]([a-z\d-]{0,61}[a-z\d]))*$',
                                   re.IGNORECASE),
                'ONLINE': re.compile(r'(.*Standby.*)|(.*OnLine.*)', re.IGNORECASE),
                'APC': re.compile(r'^apc[_-].*', re.IGNORECASE),
                'APC96': re.compile(r'^apc[_-]ap96.*', re.IGNORECASE),
                'INI': re.compile(r'^\(\s*\d+\s*,\s*\d+\s*\)\s*$'),
                'NORMAL': re.compile(r'(.*Battery Normal.*)', re.IGNORECASE)}

    mark_up_codes: Dict[str, str] = {'none':      '',
                                     'bold':      '\033[1m',
                                     # Foreground colors
                                     'white':     '\033[37m',
                                     'data':      '\033[36m',
                                     'cyan':      '\033[36m',
                                     'bcyan':     '\033[1;36m',
                                     'purple':    '\033[35m',
                                     'blue':      '\033[34m',
                                     'yellow':    '\033[33m',
                                     'green':     '\033[32m',
                                     'red':       '\033[31m',
                                     # Named formats
                                     'amd':       '\033[1;37;41m',
                                     'limit':     '\033[6;37;41m',
                                     'crit':      '\033[1;37;41m',
                                     'error':     '\033[1;37;41m',
                                     'ok':        '\033[1;37;42m',
                                     'nvidia':    '\033[1;30;42m',
                                     'warn':      '\033[1;30;43m',
                                     'other':     '\033[1;37;44m',
                                     'daemon':    '\033[1;37;44m',
                                     'label':     '\033[1;37;46m',
                                     'reset':     '\033[0;0;0m'}
    # Private items
    # Utility Repository Path Definitions
    _repository_module_path: str = os.path.dirname(str(Path(__file__).resolve()))
    _repository_path: str = os.path.join(_repository_module_path, '..')
    _local_icon_list: Dict[str, str] = {'repository': os.path.join(_repository_path, 'icons'),
                                        'debian': '/usr/share/rickslab-ups-utils/icons',
                                        'pypi-linux': '{}/.local/share/rickslab-ups-utils/icons'.format(str(Path.home()))}
    _local_config_list: Dict[str, str] = {'repository': _repository_path,
                                          'debian': '/usr/share/rickslab-ups-utils/config',
                                          'pypi-linux': '{}/.local/share/rickslab-ups-utils/config'.format(str(Path.home()))}
    _icons: Dict[str, str] = {'ups-mon': 'ups-utils-monitor.icon.png'}
    _config_file_names: Dict[str, str] = {'json': 'ups-config.json', 'ini': 'ups-utils.ini'}
    _all_args: Set[str] = {'debug', 'show_unresponsive', 'log', 'no_markup', 'ltz', 'verbose', 'sleep'}

    # Public items
    config_files: Dict[str, Union[str, None]] = {'json': None, 'ini': None}
    gui_window_title: str = 'Ricks-Lab UPS Utilities'
    gui_monitor_icon_file: str = 'ups-utils-monitor.icon.png'
    TIME_FORMAT: str = '%d-%b-%Y %H:%M:%S %z'

    def __init__(self):
        self.calling_program = ''
        self.args: Union[argparse.Namespace, None] = None
        self.program_name: Union[str, None] = None
        self.fatal: bool = False
        self.ups_json_file: Union[str, None] = None
        self.ups_config_ini: Union[str, None] = None
        self.install_type: Union[str, None] = None
        self.package_path: str = inspect.getfile(inspect.currentframe())
        # Flags used by signals
        self.quit: bool = False
        self.refresh_daemon: bool = False

        if 'dist-packages' in self.package_path: self.install_type = 'debian'
        elif '.local' in self.package_path: self.install_type = 'pypi-linux'
        else: self.install_type = 'repository'
        self._icon_path: str = self._local_icon_list[self.install_type]
        self.icon_file: str = ''

        # Set config Path
        config_list = {self.install_type: self._local_config_list[self.install_type]}
        for try_config_path in config_list.values():
            if os.path.isdir(try_config_path):
                for config_type, config_file in self._config_file_names.items():
                    if not self.config_files[config_type]:
                        if os.path.isfile(os.path.join(try_config_path, config_file)):
                            self.config_files[config_type] = os.path.join(try_config_path, config_file)
                            if not check_file(self.config_files[config_type]):
                                self.config_files[config_type] = None
            if None not in self.config_files.values():
                break
        if None in self.config_files.values():
            reset = UtConst.mark_up_codes['reset']
            color = '{}{}'.format(UtConst.mark_up_codes['red'],
                                  UtConst.mark_up_codes['bold'])
            print('Fatal: {}Missing or mis-configured configuration files.{}  Exiting...'.format(color, reset))
            print('    See man pages for {} or {} for more information.'.format(*self._config_file_names.values()))
            print('    You must first create configuration files from templates per README')
            print('    You are running with {} type installation'.format(self.install_type))
            print('    Configuration file templates are located at:\n       [{}]'.format(
                self._local_config_list[self.install_type]))
            sys.exit(-1)

        self.ups_json_file = self.config_files['json']
        self.ups_config_ini = self.config_files['ini']

        # Utility Execution Flags
        self.debug: bool = False
        self.show_unresponsive: bool = False
        self.log: bool = False
        self.no_markup: bool = False
        self.log_file_ptr: Union[TextIO, None] = None
        self.use_ltz: bool = False
        self.ltz = datetime.utcnow().astimezone().tzinfo
        self.verbose = False
        self.sleep: int = 30

    def set_env_args(self, args: argparse.Namespace, program_name: str = None) -> None:
        """
        Set arguments for the give args object.

        :param args: The object return by args parser.
        :param program_name: Name of calling program.
        """
        if program_name == 'ups-monitor':
            # Not sure why old version of ups-monitor is still installed from PyPI even
            # though I removed it from setup.py
            print('The ups-monitor executable no longer valid.  Use ups-mon instead.')
            sys.exit(-1)
        self.calling_program = program_name
        self.args = args
        if not self.ups_config_ini and program_name == 'ups-daemon':
            self.fatal = True
        for target_arg in self._all_args:
            if target_arg in self.args:
                if target_arg == 'debug': self.debug = self.args.debug
                elif target_arg == 'show_unresponsive': self.show_unresponsive = self.args.show_unresponsive
                elif target_arg == 'log': self.log = self.args.log
                elif target_arg == 'no_markup': self.no_markup = self.args.no_markup
                elif target_arg == 'verbose': self.verbose = self.args.verbose
                elif target_arg == 'sleep': self.sleep = self.args.sleep
                elif target_arg == 'ltz': self.use_ltz = self.args.ltz
        LOGGER.propagate = False
        formatter = logging.Formatter("%(levelname)s:%(name)s:%(module)s.%(funcName)s:%(message)s")
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(logging.WARNING)
        LOGGER.addHandler(stream_handler)
        LOGGER.setLevel(logging.WARNING)
        if self.args.debug:
            LOGGER.setLevel(logging.DEBUG)
            file_handler = logging.FileHandler(
                'debug_ups-utils_{}.log'.format(datetime.now().strftime("%Y%m%d-%H%M%S")), 'w')
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.DEBUG)
            LOGGER.addHandler(file_handler)
        LOGGER.debug('Install type: %s', self.install_type)
        LOGGER.debug('Calling program: %s', program_name)
        LOGGER.debug('Command line arguments:\n  %s', args)
        LOGGER.debug('Local TZ: %s', self.ltz)
        LOGGER.debug('Module directory: %s', inspect.getfile(inspect.currentframe()))
        LOGGER.debug('Icon path set to: %s', self._icon_path)
        LOGGER.debug('Config file set to: %s', self.ups_config_ini)
        LOGGER.debug('Json file set to: %s', self.ups_config_ini)
        try:
            self.icon_file = os.path.join(self._icon_path, self._icons[program_name])
        except KeyError:
            self.icon_file = None
        else:
            if not os.path.isfile(self.icon_file):
                self.process_message('Error: Icon file not found: [{}]'.format(self.icon_file), log_flag=True)

    def wrap(self, message: any, indent: int = 0, length: int = 80) -> str:
        """ Function to wrap long items at nearest space to the length limit.

        :param message:  target string to wrap
        :param indent:   indent amount for wrapped strings
        :param length:   max length of the string.
        :return:  The wrapped string.
        """
        if not isinstance(message, str): return message
        message_len = len(message)
        if message_len < length:
            return message
        trunc_loc = 0
        for i in range(length, 0, -1):
            if message[i] == ' ':
                trunc_loc = i
                break
        if trunc_loc:
            message = message[:trunc_loc] + '\n{}'.format(' '.ljust(indent, ' ')) + self.wrap(message[trunc_loc:],
                                                                                              indent, length)
        return message

    def now(self, ltz: bool = False, as_string: bool = False) -> Union[datetime, str]:
        """ Get current time

        :param ltz:  Set to True to use local time zone.
        :param as_string:  Set to True to time as a string
        :return:  Returns current time as datetime object or formatted string
        """
        now_time = datetime.now(tz=self.ltz) if ltz else datetime.now(tz=pytz.UTC)
        if as_string:
            tz_str = self.ltz if ltz else 'UTC'
            return '{} {}'.format(now_time.strftime(self.TIME_FORMAT), tz_str)
        return now_time

    @classmethod
    def process_message(cls, message: str, log_flag: bool = True, verbose: bool = False) -> None:
        """ For given message, print to stderr and/or LOGGER depending on command line options and
            the value of log_flag.

        :param message: A string containing the message to be processed.
        :param verbose:  If True, force verbose.
        :param log_flag:  If True, write to LOGGER.
        """
        if not message: return
        if verbose: print(message, file=sys.stderr)
        if log_flag: LOGGER.debug(message)

    def check_env(self) -> bool:
        """ Check the user's environment for compatibility.

        :return: True if ok
        """
        fatal = False
        # Check python version
        current_pversion = sys.version_info
        LOGGER.debug('Using python: %s', current_pversion)
        if current_pversion[:2] < __required_pversion__:
            print('Using python {}.{}.{}, but {} requires python {}.{} or higher.'.format(
                current_pversion[0], current_pversion[1], current_pversion[2],
                __program_name__, __required_pversion__[0], __required_pversion__[1]),
                file=sys.stderr)
            fatal = True

        # Check Linux Kernel version
        current_kversion_str = release()
        current_kversion = tuple([int(x) for x in re.sub('-.*', '', current_kversion_str).split('.')])
        LOGGER.debug('Using Linux Kernel: %s', current_kversion_str)
        if current_kversion < __required_kversion__:
            print('Using Linux Kernel {}, but {} requires > {}.{}.'.format(current_kversion_str,
                  __program_name__, __required_kversion__[0], __required_kversion__[1]), file=sys.stderr)
            fatal = True

        # Check if snmp tools are installed
        if not shutil.which('snmpget'):
            print('Missing dependency: `sudo apt install snmp`')
            fatal = True
        self.fatal = self.fatal or fatal
        return not fatal


UT_CONST = UtConst()
