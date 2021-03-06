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

import os
import logging
import time
from datetime import datetime
from enum import Enum

from snr.app import App

from snr.compression import Compression
from snr.yamlhelper import YAMLHelper
from snr.retention.period import PeriodDurationEnum, Periods

logger = logging.getLogger(__name__)


class RetentionTypeEnum(Enum):
    DBS = "databases"
    FILES = "files"


class Retention:
    """
    Save retention management
    """

    C_YAML = """
retention:
  - name: database_standard
    days: 5
    week: 3
    month: 1
    quarter: 1
    year: 1
  - name: file_standard
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

    def __init__(self, name,
                 last_days=5, last_weeks=1, last_months=-1, last_quarters=1, last_years=1,
                 extensions=None, retention_type=None):
        self._name = name
        self.last_days = Periods(PeriodDurationEnum.DAY, last_days)
        self.last_weeks = Periods(PeriodDurationEnum.WEEK, last_weeks)
        self.last_months = Periods(PeriodDurationEnum.MONTH, last_months)
        self.last_quarters = Periods(PeriodDurationEnum.QUARTER, last_quarters)
        self.last_years = Periods(PeriodDurationEnum.YEAR, last_years)
        self._extensions = extensions
        self._retention_type = retention_type

    @staticmethod
    def get_instance(conf, name, retention_type):
        """
        Load Retention configuration and return Retention named instance
        :param conf: file path to load
        :type conf: str
        :param name: name of the instance to instantiate
        :type name: str
        :param retention_type: indicate whether it takes SaveAtom.databases_root_path or SaveAtom.files_root_path
        :type retention_type: RetentionTypeEnum
        :return: Retention instance
        :rtype: Retention
        """
        try:
            data = YAMLHelper.load(conf)
            instance = None
            names = set()
            compression = Compression.get_instance(conf)
            for retention in data[Retention.C_RETENTION]:
                YAMLHelper.analyse_keys(
                    Retention.C_RETENTION, retention, Retention.C_RETENTION_KEYS
                )
                names.add(retention[Retention.C_RETENTION_NAME])

                if retention[Retention.C_RETENTION_NAME] == name:
                    instance = Retention(
                        retention[Retention.C_RETENTION_NAME],
                        retention[Retention.C_RETENTION_DAYS],
                        retention[Retention.C_RETENTION_WEEKS],
                        retention[Retention.C_RETENTION_MONTHS],
                        retention[Retention.C_RETENTION_QUARTERS],
                        retention[Retention.C_RETENTION_YEARS],
                        compression.extensions,
                        retention_type
                    )
            if instance is None:
                logger.error("Retention {} does not exist. You must select one of {}".format(name, names))
            return instance
        except IOError:
            logger.error("{} does not exist".format(conf))
        except (TypeError, KeyError) as e:
            logger.error("Cannot initialize retention : {}".format(e))

    @staticmethod
    def get_instances(conf):
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
    def _make_file_dict(path, extensions):
        """
        Make save file dict along with creation time.
        :return: wanted files dict
        :rtype: dict
        """
        all_files = dict()
        for root, _, files in os.walk(path):
            for file in files:
                file = os.path.join(root, file)
                if os.path.isfile(file) and not os.path.islink(file):
                    name, ext = os.path.splitext(file)
                    # get tar extension if any
                    _, tar = os.path.splitext(name)
                    # rebuild full extension
                    ext = tar + ext
                    # remove leading dot
                    ext = ext[1:]
                    if ext in extensions:
                        if root not in all_files:
                            all_files[root] = dict()
                        filedate = App.get_file_creation_date(file)
                        if filedate:
                            all_files[root][file] = datetime.strptime(filedate, App.C_DATE_FORMAT)
        return all_files

    def _get_matching_files(self, all_files):
        """
        Make wanted file list
        :param all_files: dictionary of wanted files
        :type all_files: dict
        :return: list of files to keep
        :rtype: set
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
    def _remove_unwanted_files(files, wanted_files, save_atom):
        """
        Delete all files not in wanted list
        :param files: all save files
        :type files: dict
        :param wanted_files: files to keep
        :type wanted_files: set
        :param save_atom: saveatom to retrieve app_log_prefix
        :type save_atom: SaveAtom
        :return: number of deleted files
        """
        count = 0
        for path in files.keys():
            del_files = set(files[path].keys()).difference(wanted_files)
            for file in del_files:
                logger.info("{}: Deleting {}".format(save_atom.app_log_prefix(), file))
                os.remove(file)
                count += 1
        return count

    def run(self, save_atom):
        """
        runs retention on specified SaveAtom according to retention_type value
        :param save_atom:
        :type save_atom: SaveAtom
        :return:
        """
        start = time.time()
        path = save_atom.databases_root_path
        if self._retention_type == RetentionTypeEnum.FILES:
            path = save_atom.files_root_path

        logger.info("{}: Starting retention on {}".format(save_atom.app_log_prefix(), path))
        files = Retention._make_file_dict(path, self._extensions)
        wanted_files = self._get_matching_files(files)
        count = Retention._remove_unwanted_files(files, wanted_files, save_atom)
        logger.info(
            "{}: Finished retention on {}. Deleted {} files in {}s".format(
                save_atom.app_log_prefix(), path, count, time.time()-start
            )
        )
