#!/bin/bash
#
#   ups-utils  -  A set of utilities for the management of UPS from a linux host
#
#   shutdownBOINC.sh  -  A sample shutdown script for a BOINC client
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

if [ -z "${BOINC_HOME}" ]; then
  echo "BOINC_HOME not set."
  exit 1
  fi

if ! cd "${BOINC_HOME}"; then
  echo "Not able to cd to ${BOINC_HOME}."
  exit 1
  fi

LOG_FILE="BOINC_Power.log"
echo "$(date): shutting down" >> $LOG_FILE

quitBOINC.sh
shutdown +2 'UPS battery depleted.  System will shutdown in 2min.'

exit 0