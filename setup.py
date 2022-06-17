#!/usr/bin/python3
""" setup.py used in producing source and binary distributions.

    Usage: python3 setup.py sdist bdist_wheel

    Copyright (C) 2020  RicksLab

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
__author__ = 'RicksLabs'
__copyright__ = 'Copyright (C) 2020 RicksLab'
__license__ = 'GPL-3'
__program_name__ = 'setup.py'
__maintainer__ = 'RicksLab'
__docformat__ = 'reStructuredText'

# pylint: disable=line-too-long

import sys
import os
import pathlib
from setuptools import setup, find_packages
from UPSmodules import __version__, __status__, __required_pversion__, __credits__

if sys.version_info[:2] < __required_pversion__:
    print('rickslab-ups-utils requires at least Python {}.{}.'.format(__required_pversion__[0],
                                                                      __required_pversion__[1]))
    sys.exit(1)

with open(os.path.join(pathlib.Path(__file__).parent, 'README.md'), 'r') as file_ptr:
    long_description = file_ptr.read()

setup(name='rickslab-ups-utils',
      version=__version__,
      description='Ricks-Lab UPS Utilities',
      long_description_content_type='text/markdown',
      long_description=long_description,
      author=__author__,
      keywords='ups system monitoring apc eaton linux boinc',
      platforms='posix',
      author_email='rueikes.homelab@gmail.com',
      url='https://github.com/Ricks-Lab/ups-utils',
      packages=find_packages(include=['UPSmodules']),
      include_package_data=True,
      scripts=['ups-ls', 'ups-daemon', 'ups-mon', 'cancelShutdownBOINC.sh', 'pauseBOINC.sh',
               'quitBOINC.sh', 'resumeBOINC.sh', 'shutdownBOINC.sh'],
      license=__license__,
      python_requires='>={}.{}'.format(__required_pversion__[0], __required_pversion__[1]),
      project_urls={'Bug Tracker':   'https://github.com/Ricks-Lab/ups-utils/issues',
                    'Documentation': 'https://github.com/Ricks-Lab/ups-utils/',
                    'Source Code':   'https://github.com/Ricks-Lab/ups-utils'},
      classifiers=[__status__,
                   'Operating System :: POSIX',
                   'Natural Language :: English',
                   'Programming Language :: Python :: 3',
                   'Topic :: System :: Power (UPS)',
                   'Topic :: System :: Monitoring',
                   'License :: OSI Approved :: GNU General Public License v3 (GPLv3)'],
      install_requires=['pytz>=2019.3'],
      data_files=[('share/rickslab-ups-utils/icons', ['icons/ups-utils-monitor.icon.png']),
                  ('share/rickslab-ups-utils/doc', ['README.md', 'LICENSE']),
                  ('share/rickslab-ups-utils/config', ['ups-utils.ini.template',
                                                       'ups-config.json.template']),
                  ('share/man/man1', ['man/ups-ls.1',
                                      'man/ups-daemon.1',
                                      'man/ups-mon.1']),
                  ('share/man/man4', ['man/ups-config.json.4',
                                      'man/ups-util.ini.4'])])
