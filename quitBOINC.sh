#!/bin/bash
#
#   ups-utils  -  A set of utilities for the management of UPS from a linux host
#
#   quitBOINC.sh  -  A sample pause script for a BOINC client
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

if [ -z "${BOINC_HOME}" ]; then
  echo "BOINC_HOME not set."
  exit 1
  fi

if ! cd "${BOINC_HOME}"; then
  echo "Not able to cd to ${BOINC_HOME}."
  exit 1
  fi

LOG_FILE="BOINC_Power.log"
echo "$(date): quitting BOINC" >> ${LOG_FILE}

BOINCCMD="${BOINC_HOME}boinccmd"
if ! [ -x "${BOINCCMD}" ]; then
  echo "${BOINCCMD} executable not found." >> "${LOG_FILE}"
  exit 1
  fi

$BOINCCMD --get_project_status \
	  | sed -n -e '/master URL:/s/.\+URL://p' \
	  | while read ; do \
	    $BOINCCMD --project $REPLY suspend \
	  ; done

$BOINCCMD --quit >> $LOG_FILE

exit 0