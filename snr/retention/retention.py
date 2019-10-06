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
import sys
import logging

from snr.retention.period import PeriodDurationEnum, Periods

logger = logging.getLogger(__name__)


class Retention:
    """
    Save retention management
    """

    def __init__(self, path, last_days=5, last_week=1, last_month=-1, last_quarter=1, last_year=1):
        self.path = path
        self.last_days = Periods.get_instance(PeriodDurationEnum.DAY.value, last_days)
        self.last_week = Periods.get_instance(PeriodDurationEnum.WEEK.value, last_week)
        self.last_month = Periods.get_instance(PeriodDurationEnum.MONTH.value, last_month)
        self.last_quarter = Periods.get_instance(PeriodDurationEnum.QUARTER.value, last_quarter)
        self.last_year = Periods.get_instance(PeriodDurationEnum.YEAR.value, last_year)

        self._all_files = dict()
        self._all_wanted_file = list()

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

                        all_files[root][file] = os.path.getctime(file)
                else:
                    logger.warning("Skipping link {}".format(file))
        return all_files

    def _get_matching_files(self):
        """
        Make wanted file list
        :return: list of files to keep
        :rtype: list
        """
        all_wanted_file = list()
        for path in self._all_files.keys():
            self._all_wanted_file.extend(self.last_year.get_matching_files_list(self._all_files[path]))
            self._all_wanted_file.extend(self.last_quarter.get_matching_files_list(self._all_files[path]))
            self._all_wanted_file.extend(self.last_month.get_matching_files_list(self._all_files[path]))
            self._all_wanted_file.extend(self.last_week.get_matching_files_list(self._all_files[path]))
            self._all_wanted_file.extend(self.last_days.get_matching_files_list(self._all_files[path]))

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

    def run(self):
        logger.info("Starting retention on {}", self.path)
        self._all_files = Retention._make_file_dict(self.path)
        self._all_wanted_file = self._get_matching_files()
        Retention._remove_unwanted_files(self.path, self._all_wanted_file)


def load_retention(retentions_param):
    """Charge une liste de classe Retention avec les paramètres entrés"""
    retentions = list()

    for retention_param in retentions_param:
        retentions.append(Retention(*retention_param))

    return retentions

#charge le fichier de configuration
sys.path.append("/etc/save")
import retention_conf

#charge les opérations de rétention à faire
retentions = load_retention(retention_conf.retentions)

for retention in retentions:
    retention.run()


