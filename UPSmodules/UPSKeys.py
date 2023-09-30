#!/usr/bin/env python3
""" Project Keys as Enum Classes

    Copyright (C) 2023  RicksLab

    This program is free software: you can redistribute it and/or modify it
    under the terms of the GNU General Public License as published by the Free
    Software Foundation, either version 3 of the License, or (at your option)
    any later version.

    This program is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
    FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
    more details.

    You should have received a copy of the GNU General Public License along with
    this program.  If not, see <https://www.gnu.org/licenses/>.
"""
__author__ = 'RicksLab'
__credits__ = ['']
__copyright__ = 'Copyright (C) 2023 RicksLab'
__license__ = 'GNU General Public License'
__program_name__ = 'gpu-utils'
__maintainer__ = 'RicksLab'
__docformat__ = 'reStructuredText'

# pylint: disable=multiple-statements
# pylint: disable=line-too-long
# pylint: disable=logging-format-interpolation
# pylint: disable=consider-using-f-string
# pylint: disable=invalid-name

from typing import List
from enum import Enum, auto


class UpsEnum(Enum):
    """ Define Critical dictionary/dataFrame keys and Enum objects. Be careful when modifying. A change
        in enum value could invalidate saved pickled model parameters.
    """
    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return self.__str__()

    @classmethod
    def list(cls) -> List[str]:
        """ Return a list of name from current UpsEnum object """
        return list(map(lambda c: c.name, cls))


class UpsType(UpsEnum):
    """ Enum object to define keys for UPS type.
    """
    all = auto()
    none = auto()
    apc_ap96xx = auto()
    eaton_pw = auto()


class UpsStatus(UpsEnum):
    """ Enum object to define keys for UPS status.
    """
    all = auto()
    valid = auto()
    compatible = auto()
    accessible = auto()
    responsive = auto()
    daemon = auto()


class MibGroup(UpsEnum):
    """ Enum object to define keys for UPS status.
    """
    all = auto()
    all_apc = auto()
    all_eaton = auto()
    monitor = auto()
    output = auto()
    input = auto()
    static = auto()
    dynamic = auto()


class TxtStyle(UpsEnum):
    """ Enum object to define keys for UPS text style.
    """
    warn = auto()
    crit = auto()
    green = auto()
    bold = auto()
    normal = auto()
    daemon = auto()


class MarkUpCodes(UpsEnum):
    """ Enum object to define keys for UPS text mark up.
    """
    none = auto()
    bold = auto()
    white = auto()
    data = auto()
    cyan = auto()
    bcyan = auto()
    purple = auto()
    blue = auto()
    yellow = auto()
    green = auto()
    red = auto()
    amd = auto()
    limit = auto()
    crit = auto()
    error = auto()
    ok = auto()
    nvidia = auto()
    warn = auto()
    other = auto()
    daemon = auto()
    label = auto()
    reset = auto()


