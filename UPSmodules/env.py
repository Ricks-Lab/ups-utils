#!/usr/bin/env python3
"""env.py - sets environment for ups-utils and establishes global variables

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
__author__ = 'RueiKe'
__copyright__ = 'Copyright (C) 2019 RicksLab'
__credits__ = []
__license__ = 'GNU General Public License'
__program_name__ = 'ups-utils'
__maintainer__ = 'RueiKe'
__docformat__ = 'reStructuredText'
# pylint: disable=multiple-statements
# pylint: disable=line-too-long
# pylint: disable=bad-continuation

import argparse
import platform
import sys
import os
import re
import logging
from pathlib import Path
import shutil
from datetime import datetime
from UPSmodules import __version__, __status__

LOGGER = logging.getLogger('ups-utils')


class UtConst:
    """ Class definition for UPS Utils environment"""
    # FQDN regex credit: https://stackoverflow.com/questions/2532053/validate-a-hostname-string
    # IPV6 regex credit: https://gist.github.com/syzdek/6086792
    PATTERNS = {'HEXRGB': re.compile(r'^#[0-9a-fA-F]{6}'),
                'SNMP_VALUE': re.compile(r'.*=.*:.*'),
                'IPV4': re.compile(r'^([0-9]{1,3})(.[0-9]{1,3}){3}$'),
                'IPV6': re.compile(r'^(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|'
                                   r'([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}'
                                   r'(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|'
                                   r'([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}'
                                   r'(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|'
                                   r':((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|'
                                   r'::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}'
                                   r'(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|'
                                   r'(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9])'
                                   r'{0,1}[0-9]))$'),
                'FQDN': re.compile(r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9]))*$',
                                   re.IGNORECASE),
                'ONLINE': re.compile(r'(.*Standby.*)|(.*OnLine.*)'),
                'INI': re.compile(r'^\(\s*[0-9]+\s*,\s*[0-9]+\s*\)\s*$'),
                'NORMAL': re.compile(r'(.*Battery Normal.*)')}

    # Constant path and file names
    UPS_JSON_FILE = 'ups-config.json'
    UPS_CONFIG_INI = 'ups-utils.ini'
    # Utility Repository Path Definitions
    _repository_module_path = os.path.dirname(str(Path(__file__).resolve()))
    _repository_path = os.path.join(_repository_module_path, '..')
    _local_icon_list = [os.path.join(_repository_path, 'icons'),
                        '/usr/share/rickslab-ups-utils/icons',
                        '{}/.local/share/rickslab-ups-utils/icons'.format(str(Path.home()))]
    _local_config_list = [_repository_path,
                          '/usr/share/rickslab-ups-utils/config',
                          '{}/.local/share/rickslab-ups-utils/config'.format(str(Path.home()))]
    gui_window_title = 'Ricks-Lab UPS Utilities'
    gui_monitor_icon_file = 'ups-utils-monitor.icon.png'

    def __init__(self):
        self.args = None

        # Set config Path
        for try_config_path in UtConst._local_config_list:
            if os.path.isdir(try_config_path):
                if os.path.isfile(os.path.join(try_config_path, self.UPS_CONFIG_INI)) and \
                   os.path.isfile(os.path.join(try_config_path, self.UPS_JSON_FILE)):
                    self.ups_json_file = os.path.join(try_config_path, self.UPS_JSON_FILE)
                    self.ups_config_ini = os.path.join(try_config_path, self.UPS_CONFIG_INI)
                    break
        else:
            self.ups_json_file = None
            self.ups_config_ini = None
            print('Missing required configuration files.  Exiting...')
            print('     See man pages for {} or {} for more information.'.format(self.UPS_JSON_FILE,
                                                                                 self.UPS_CONFIG_INI))
            sys.exit(-1)

        # Set Icon Path
        for try_icon_path in UtConst._local_icon_list:
            if os.path.isdir(try_icon_path):
                if os.path.isfile(os.path.join(try_icon_path, self.gui_monitor_icon_file)):
                    self.icon_path = try_icon_path
                    break
        else:
            self.icon_path = None

        # Utility Execution Flags
        self.show_unresponsive = False
        self.LOG = False
        self.log_file_ptr = ''
        self.USELTZ = False
        self.LTZ = datetime.utcnow().astimezone().tzinfo

    def set_env_args(self, args: argparse.Namespace) -> None:
        """
        Set arguments for the give args object.

        :param args: The object return by args parser.
        """
        self.args = args
        for target_arg in vars(self.args):
            if target_arg == 'show_unresponsive': self.show_unresponsive = self.args.show_unresponsive
            elif target_arg == 'log': self.LOG = self.args.log
            elif target_arg == 'ltz': self.USELTZ = self.args.ltz
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
        LOGGER.debug('Command line arguments:\n  %s', args)
        LOGGER.debug('Local TZ: %s', self.LTZ)
        LOGGER.debug('Icon path set to: %s', self.icon_path)

    @staticmethod
    def now(ltz: bool = False) -> datetime:
        """ Get current time

        :param ltz:  Set to True to use local time zone.
        :return:  Returns current time as datetime object
        """
        if ltz:
            return datetime.now()
        return datetime.utcnow()

    @staticmethod
    def check_env() -> int:
        """ Check the user's environment for compatibility.

        :return: Returns an integer indicating env error code: 0 for passes.
        """
        # Check python version
        required_pversion = [3, 6]
        (python_major, python_minor, python_patch) = platform.python_version_tuple()
        LOGGER.debug('Using python %s.%s.%s', python_major, python_minor, python_patch)
        if int(python_major) < required_pversion[0]:
            print('Using python' + python_major + ', but ' + __program_name__ +
                  ' requires python ' + str(required_pversion[0]) + '.' + str(required_pversion[1]) + ' or higher.',
                  file=sys.stderr)
            return -1
        elif int(python_major) == required_pversion[0] and int(python_minor) < required_pversion[1]:
            print('Using python ' + python_major + '.' + python_minor + '.' + python_patch + ', but ' +
                  __program_name__ + ' requires python ' + str(required_pversion[0]) + '.' +
                  str(required_pversion[1]) + ' or higher.', file=sys.stderr)
            return -1

        # Check Linux Kernel version
        required_kversion = [4, 8]
        linux_version = platform.release()
        if int(linux_version.split('.')[0]) < required_kversion[0]:
            print('Using Linux Kernel ' + linux_version + ', but ' + __program_name__ + ' requires > ' +
                  str(required_kversion[0]) + '.' + str(required_kversion[1]), file=sys.stderr)
            return -2
        elif int(linux_version.split('.')[0]) == required_kversion[0] and \
                                                 int(linux_version.split('.')[1]) < required_kversion[1]:
            print('Using Linux Kernel ' + linux_version + ', but ' + __program_name__ + ' requires > ' +
                  str(required_kversion[0]) + '.' + str(required_kversion[1]), file=sys.stderr)
            return -2

        # Check if snmp tools are installed
        if not shutil.which('snmpget'):
            print('Missing dependency: `sudo apt install snmp`')
            return -3

        return 0


UT_CONST = UtConst()


def about() -> None:
    """ Display details about this module.

    :return:  None
    """
    print(__doc__)
    print('Author: ', __author__)
    print('Copyright: ', __copyright__)
    print('Credits: ', __credits__)
    print('License: ', __license__)
    print('Version: ', __version__)
    print('Maintainer: ', __maintainer__)
    print('Status: ', __status__)
    sys.exit(0)


if __name__ == '__main__':
    about()
