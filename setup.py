#!/usr/bin/python3

import sys
import os
import pathlib
from setuptools import setup
from UPSmodules import __version__, __status__

if sys.version_info < (3, 6):
    print('rickslab-ups-utils requires at least Python 3.6.')
    sys.exit(1)

with open(os.path.join(pathlib.Path(__file__).parent, 'README.md'), 'r') as file_ptr:
    long_description = file_ptr.read()

setup(name='rickslab-ups-utils',
      version=__version__,
      description='Ricks-Lab UPS Utilities',
      long_description_content_type='text/markdown',
      long_description=long_description,
      author='RicksLabs',
      keywords='ups system monitoring apc eaton linux boinc',
      platforms='posix',
      author_email='rueikes.homelab@gmail.com',
      url='https://github.com/Ricks-Lab/ups-utils',
      packages=['UPSmodules'],
      include_package_data=True,
      scripts=['ups-ls', 'ups-daemon', 'ups-monitor', 'cancelShutdownBOINC.sh', 'pauseBOINC.sh',
               'quitBOINC.sh', 'resumeBOINC.sh', 'shutdownBOINC.sh'],
      license='GPL-3',
      python_requires='==3.6',
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
                  ('share/rickslab-ups-utils/config', ['ups-utils.ini.template', 'ups-config.json.template']),
                  ('share/man/man1', ['man/ups-ls.1',
                                      'man/ups-daemon.1',
                                      'man/ups-monitor.1']),
                  ('share/man/man4', ['man/ups-config.json.4',
                                      'man/ups-util.ini.4'])]
      )
