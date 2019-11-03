# -*- coding: utf8 -*-
# ------------------------------------------------------------------------------
# Name:        units
# Purpose:     Unit conversion
#
#
# Author:      Jonathan Besanceney <jonathan.besanceney@gmail.com>
#
#
# Created:     03/11/2019
# Copyright:   (c) 2019 snr
#
# Licence:     LGPLv3 2016.
#
# This file is a part of snr.
#
#    snr is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    snr is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with snr.  If not, see <http://www.gnu.org/licenses/>.
# ------------------------------------------------------------------------------
import datetime


class Units:
    """
    Helpers to display human readable measures
    """
    VALUE = 0
    UNIT = 1
    BYTE = [1, 'B']
    KB = [1024 * BYTE[VALUE], 'KB']
    MB = [1024 * KB[VALUE], 'MB']
    GB = [1024 * MB[VALUE], 'GB']
    TB = [1024 * GB[VALUE], 'TB']
    PB = [1024 * TB[VALUE], 'PB']
    SIZE_UNITS = [PB, TB, GB, MB, KB, BYTE]

    @staticmethod
    def convert_seconds(s):
        """
        :param s: seconds
        :type s: float
        :return: converted time
        :rtype: str
        """
        return str(datetime.timedelta(seconds=s))

    @staticmethod
    def convert_bytes(b):
        """
        :param b: bytes
        :type b: int
        :return: converted
        """
        for unit in Units.SIZE_UNITS:
            s = b / unit[Units.VALUE]
            if s >= 1:
                return '{0}{1}'.format(round(s, ndigits=2), unit[Units.UNIT])

    @staticmethod
    def get_bitrate(b, s):
        """
        Compute bitrate from bytes and seconds and convert it to human readable str
        :param b: bytes
        :type b: int
        :param s: seconds
        :type s: float
        :return: String representing bitrate
        """
        byte_per_sec = round(b / s)
        return Units.convert_bytes(byte_per_sec) + '/s'
