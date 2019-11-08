#!/bin/bash
#
#   ups-utils  -  A set of utilities for the management of UPS from a linux host
#
#   resumeSETI.sh  -  A sample resume script for a BOINC client
#
#   Copyright (C) 2019  RueiKe
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.

cd /home/boinc/BOINC/
echo "`date`: resuming SETI" >> SETI_Power.log
/home/boinc/BOINC/boinccmd --project http://setiathome.berkeley.edu/ resume >> SETI_Power.log
shutdown -c
