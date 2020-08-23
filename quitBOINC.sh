#!/bin/bash
#
#   ups-utils  -  A set of utilities for the management of UPS from a linux host
#
#   pauseSETI.sh  -  A sample pause script for a BOINC client
#
#   Copyright (C) 2019  RicksLab
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

LOG_FILE="BOINC_Power.log"
BOINC_HOME="/home/boinc/BOINC/"
BOINCCMD="${BOINC_HOME}boinccmd"
cd $BOINC_HOME || exit
echo "$(date): pausing BOINC" >> $LOG_FILE
$BOINCCMD --get_project_status \
	  | sed -n -e '/master URL:/s/.\+URL://p' \
	  | while read ; do \
	    $BOINCCMD --project $REPLY suspend \
	  ; done
$BOINCCMD --quit >> $LOG_FILE
