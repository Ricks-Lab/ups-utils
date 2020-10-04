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
    PATTERNS = {'HEXRGB': re.compile(r'^#[0-9a-fA-F]{6}'),
                'SNMP_VALUE': re.compile(r'.*=.*:.*'),
                'IPV4': re.compile(r'^([0-9]{1,3})(.[0-9]{1,3}){3}$'),
                'ONLINE': re.compile(r'(.*Standby.*)|(.*OnLine.*)'),
                'INI': re.compile(r'^\(\s*[0-9]+\s*,\s*[0-9]+\s*\)\s*$'),
                'NORMAL': re.compile(r'(.*Battery Normal.*)')}
    _local_icon_list = ['{}/.local/share/rickslab-ups-utils/icons'.format(str(Path.home())),
                        '/usr/share/rickslab-ups-utils/icons']
    gui_window_title = 'Ricks-Lab UPS Utilities'

    def __init__(self):
        self.args = None
        # Utility Path Definitions
        self.repository_module_path = os.path.dirname(str(Path(__file__).resolve()))
        self.repository_path = os.path.join(self.repository_module_path, '..')
        self.config_dir = os.path.join(os.getenv('HOME'), '.ups-utils/')
        self.dist_share = '/usr/share/ricks-ups-utils/'
        self.dist_icons = os.path.join(self.dist_share, 'icons')

        # Set Icon Path
        self._local_icon_list.append(os.path.join(self.repository_path, 'icons'))
        for try_icon_path in UtConst._local_icon_list:
            if os.path.isdir(try_icon_path):
                self.icon_path = try_icon_path
                break
        else:
            self.icon_path = None

        # Configuration Parameters
        self.ERROR_json = False
        self.UPS_LIST_JSON_FILE = 'config.json'
        self.UPS_CONFIG_INI = 'ups-utils.ini'

        # Utility Execution Flags
        self.show_unresponsive = False
        self.DEBUG = False
        self.LOG = False
        self.log_file_ptr = ''
        self.USELTZ = False
        self.LTZ = datetime.utcnow().astimezone().tzinfo

    def set_env_args(self, args) -> None:
        """
        Set arguments for the give args object.

        :param args: The object return by args parser.
        """
        self.args = args
        for target_arg in vars(self.args):
            if target_arg == 'debug': self.DEBUG = self.args.debug
            elif target_arg == 'show_unresponsive': self.show_unresponsive = self.args.show_unresponsive
            elif target_arg == 'log': self.LOG = self.args.log
            elif target_arg == 'ltz': self.USELTZ = self.args.ltz
        LOGGER.propagate = False
        formatter = logging.Formatter("%(levelname)s:%(name)s:%(module)s.%(funcName)s:%(message)s")
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(logging.WARNING)
        LOGGER.addHandler(stream_handler)
        LOGGER.setLevel(logging.WARNING)
        if self.DEBUG:
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
    def now(ltz=False):
        """ Get current time
        :param ltz:  Set to True to use local time zone.
        :type ltz: bool
        :return:  Returns current time as datetime object
        :rtype: datetime
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
            print('Missing dependency: sudo apt install snmp')
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
