# -*- coding: utf8 -*-
# ------------------------------------------------------------------------------
# Name:        retention
# Purpose:     save retention
#
#
# Author:      Jonathan Besanceney <jonathan.besanceney@gmail.com>
#
#
# Created:     08/09/2019
# Copyright:   (c) 2019 docker
#
# Licence:     LGPLv3 2016.
#
# This file is a part of docker.
#
#    docker is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    docker is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with docker.  If not, see <http://www.gnu.org/licenses/>.
# ------------------------------------------------------------------------------

import os
import logging
from datetime import datetime

from snr.yamlhelper import YAMLHelper
from snr.retention.period import PeriodDurationEnum, Periods

logger = logging.getLogger(__name__)


class Retention:
    """
    Save retention management

    retention:
      - name: database_standard:
        days: 5
        week: 3
        month: 1
        quarter: 1
        year: 1
      - name: file_standard:
        days: 1
        week: -1
        month: -1
        quarter: -1
        year: -1
    """
    C_RETENTION = 'retention'
    C_RETENTION_NAME = 'name'
    C_RETENTION_DAYS = 'days'
    C_RETENTION_WEEKS = 'week'
    C_RETENTION_MONTHS = 'month'
    C_RETENTION_QUARTERS = 'quarter'
    C_RETENTION_YEARS = 'year'
    C_RETENTION_KEYS = {
        C_RETENTION_NAME,
        C_RETENTION_DAYS, C_RETENTION_WEEKS, C_RETENTION_MONTHS, C_RETENTION_QUARTERS, C_RETENTION_YEARS
    }

    def __init__(self, name, last_days=5, last_weeks=1, last_months=-1, last_quarters=1, last_years=1):
        self._name = name
        self.last_days = Periods.get_instance(PeriodDurationEnum.DAY, last_days)
        self.last_weeks = Periods.get_instance(PeriodDurationEnum.WEEK, last_weeks)
        self.last_months = Periods.get_instance(PeriodDurationEnum.MONTH, last_months)
        self.last_quarters = Periods.get_instance(PeriodDurationEnum.QUARTER, last_quarters)
        self.last_years = Periods.get_instance(PeriodDurationEnum.YEAR, last_years)

    @staticmethod
    def get_retentions(conf):
        """
        Load Retention configuration and return Retention instances
        :param conf: file path to load
        :return: dict of Retention instances
        :rtype: dict
        """
        try:
            data = YAMLHelper.load(conf)

            instances = dict()
            for retention in data[Retention.C_RETENTION]:
                YAMLHelper.analyse_keys(
                    Retention.C_RETENTION, retention, Retention.C_RETENTION_KEYS
                )
                instances[retention[Retention.C_RETENTION_NAME]] = Retention(
                    retention[Retention.C_RETENTION_NAME],
                    retention[Retention.C_RETENTION_DAYS],
                    retention[Retention.C_RETENTION_WEEKS],
                    retention[Retention.C_RETENTION_MONTHS],
                    retention[Retention.C_RETENTION_QUARTERS],
                    retention[Retention.C_RETENTION_YEARS],
                )
            return instances

        except IOError:
            logger.error("{} does not exist".format(conf))
        except (TypeError, KeyError) as e:
            logger.error("Cannot initialize retentions : {}".format(e))


    @staticmethod
    def _make_file_dict(path):
        """
        Make save file dict along with creation time.
        :return: wanted files dict
        :rtype: dict
        """
        all_files = dict()
        for root, _, files in os.walk(path):
            for file in files:
                file = os.path.join(root, file)
                if not os.path.islink(file):
                    ext = os.path.splitext(file)
                    if ext[1] == ".xz" or ext[1] == ".tar.xz":
                        if root not in all_files:
                            all_files[root] = dict()

                        all_files[root][file] = datetime.fromtimestamp(os.path.getctime(file))
                else:
                    logger.warning("Skipping link {}".format(file))
        return all_files

    def _get_matching_files(self, all_files):
        """
        Make wanted file list
        :param all_files: dictionary of wanted files
        :type all_files: dict
        :return: list of files to keep
        :rtype: list
        """
        all_wanted_file = set()
        for path in all_files.keys():
            all_wanted_file.update(self.last_years.get_matching_files_list(all_files[path]))
            all_wanted_file.update(self.last_quarters.get_matching_files_list(all_files[path]))
            all_wanted_file.update(self.last_months.get_matching_files_list(all_files[path]))
            all_wanted_file.update(self.last_weeks.get_matching_files_list(all_files[path]))
            all_wanted_file.update(self.last_days.get_matching_files_list(all_files[path]))

        return all_wanted_file

    @staticmethod
    def _remove_unwanted_files(path, wanted_files):
        """
        Delete all files not in wanted list
        :param path: path to clean
        :type path: str
        :param wanted_files: files to keep
        :type wanted_files: list
        """

        for root, _, files in os.walk(path):
            for file in files:
                file = os.path.join(root, file)
                if not os.path.islink(file):
                    ext = os.path.splitext(file)
                    if ext[1] == ".xz" or ext[1] == ".tar.xz":
                        if file not in wanted_files:
                            logger.info("Deleting {}".format(file))
                            os.remove(file)
                else:
                    logger.warning("Skipping link {}".format(file))

    def run(self, path):
        logger.info("Starting retention on {}".format(path))
        all_files = Retention._make_file_dict(path)
        all_wanted_files = self._get_matching_files(all_files)
        Retention._remove_unwanted_files(path, all_wanted_files)

