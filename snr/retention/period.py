# -*- coding: utf8 -*-
# ------------------------------------------------------------------------------
# Name:        period
# Purpose:     
#
#
# Author:      Jonathan Besanceney <jonathan.besanceney@gmail.com>
#
#
# Created:     06/10/2019
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

from datetime import timedelta, datetime, date
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PeriodDurationEnum(Enum):
    DAY = 1
    WEEK = 7
    MONTH = 28
    QUARTER = 91
    YEAR = 365


class Period:
    """
    Period definition.
    """

    def __init__(self, start, duration, latest=False):
        """
        :param start: datetime for the day
        :type start: datetime
        :param duration: number of days of this Period
        :type duration: snr.retention.period.PeriodDurationEnum
        :param latest: optional. Select earliest per default, except for one day duration
        :type latest: bool
        """
        self._start = start
        self._duration = duration
        self._latest = latest

        if duration == PeriodDurationEnum.DAY:
            self._latest = True
        self._end = start - timedelta(days=self._duration.value)
        logger.debug(
            "{} Period initialized from {} to {}. Select latest file {}".format(
                duration, start, self._end, self._latest
            )
        )

    @staticmethod
    def cache_reset():
        Period.cache.clear()

    @property
    def start(self):
        return self._start

    @property
    def end(self):
        return self._end

    @property
    def duration(self):
        return self._duration

    @property
    def latest(self):
        return self._latest

    def __repr__(self):
        return "Period(duration={}, start={}, end={}, latest={})".format(
            self._duration,
            self._start,
            self._end,
            self._latest
        )

    def get_matching_file(self, file_dict):
        """
        Select oldest file in the list unless self._latest is set to False
        :type file_dict: dict
        :rtype: str()
        """

        # http://docs.python.org/3.3/faq/programming.html#is-there-an-equivalent-of-c-s-ternary-operator
        selected_date = self._end if self._latest else self._start
        selected_file = ""

        for file in file_dict.keys():
            file_date = file_dict[file]

            if self._start >= file_date >= self._end:
                if self._latest and selected_date < file_date:
                    selected_date = file_date
                    selected_file = file
                elif not self._latest and selected_date > file_date:
                    selected_date = file_date
                    selected_file = file

        if selected_file != "":
            logger.debug("{} Period, keeping {} ".format(self._duration, selected_file))

        return selected_file


class Periods:
    """
    Defines Period.
    """

    def __init__(self, period_length, number_of_period):
        """
        :param period_length: length in days
        :type period_length: PeriodDurationEnum
        :param number_of_period: how many period instanciate from now
        :type number_of_period: int
        """

        self._period_length = period_length
        self._number_of_period = number_of_period
        self._period_list = list()

        period_start = datetime.today()

        i = 0
        while i < self._number_of_period:
            p_instance = Period(period_start, self._period_length)
            self._period_list.append(p_instance)
            period_start = p_instance.end
            i += 1

    def get_matching_files_list(self, file_dict):
        """
        :param file_dict: file dictionary
        :type file_dict: dict
        :return: matching file list
        :rtype: set
        """

        selected_file_list = set()

        for p in self._period_list:
            selected_file = p.get_matching_file(file_dict)
            if selected_file != "":
                selected_file_list.add(selected_file)

        return selected_file_list
