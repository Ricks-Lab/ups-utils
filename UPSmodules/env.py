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
__copyright__ = 'Copyright (C) 2019 RueiKe'
__credits__ = []
__license__ = 'GNU General Public License'
__program_name__ = 'ups-utils'
__version__ = 'v0.9.0'
__maintainer__ = 'RueiKe'
__status__ = 'Beta Release'

import platform
import sys
import os
from pathlib import Path
import shutil
from datetime import datetime


class UT_CONST:
    def __init__(self):
        # Utility Path Definitions
        self.repository_module_path = os.path.dirname(str(Path(__file__).resolve()))
        self.repository_path = os.path.join(self.repository_module_path, '..')
        self.config_dir = os.path.join(os.getenv('HOME'), '.ups-utils/')
        self.dist_share = '/usr/share/ricks-ups-utils/'
        self.dist_icons = os.path.join(self.dist_share, 'icons')
        if os.path.isdir(self.dist_icons):
            self.icon_path = self.dist_icons
        else:
            self.icon_path = os.path.join(self.repository_path, 'icons')

        # Configuration Parameters
        self.ERROR_config = False
        self.ERROR_json = False
        self.UPS_LIST_JSON_FILE = 'config.json'
        # Config.py defaults
        self.DEFAULT_MONITOR_READ_INTERVAL = 10
        self.DEFAULT_DAEMON_READ_INTERVAL = 30
        self.READ_INTERVAL_LIMIT = 5
        # Daemon and Monitor defaults in tuples (critical, warning, limit)
        self.def_threshold_battery_time_rem = (5, 10, 4)
        self.def_threshold_time_on_battery = (5, 3, 1)
        self.def_threshold_battery_load = (90, 80, 10)
        self.def_threshold_battery_capacity = (10, 50, 5)

        # Utility Execution Flags
        self.show_unresponsive = False
        self.DEBUG = False
        self.LOG = False
        self.log_file_ptr = ''
        self.USELTZ = False
        self.LTZ = datetime.utcnow().astimezone().tzinfo
        if self.DEBUG: print('Local TZ: %s' % str(self.LTZ))

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

    def check_env(self):
        """ Check the user's environment for compatibility.
        :return: Returns an integer indicating env error code: 0 for passes
        :rtype: int
        """
        # Check python version
        required_pversion = [3, 6]
        (python_major, python_minor, python_patch) = platform.python_version_tuple()
        if self.DEBUG: print('Using python ' + python_major + '.' + python_minor + '.' + python_patch)
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


ut_const = UT_CONST()


def about():
    """ Display details about this module.
    :return:  None
    :rtype:  None
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
