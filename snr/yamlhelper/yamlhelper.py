# -*- coding: utf8 -*-
# ------------------------------------------------------------------------------
# Name:        yamlhelper
# Purpose:     
#
#
# Author:      Jonathan Besanceney <jonathan.besanceney@gmail.com>
#
#
# Created:     15/09/2019
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
import sys
import logging
from yaml import load, YAMLError
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader
from yaml.parser import ParserError

logger = logging.getLogger(__name__)


class YAMLHelper:
    cache = dict()

    @staticmethod
    def load(file, reload=False):
        """
        Load YAML file and returns data dict
        :param file: YAML data filepath
        :type file: str
        :param reload: Optional. Reset cache
        :type reload: bool
        :return: data dictionary
        :rtype: dict
        """
        if file not in YAMLHelper.cache.keys() or reload:
            try:
                with open(file, 'r') as f:
                    data = load(f, Loader=Loader)
                YAMLHelper.cache[file] = data
            except (ParserError, YAMLError) as e:
                logger.error("Aborting : {}".format(e))
                sys.exit(1)
            except FileNotFoundError as e:
                logger.error("Aborting : {}".format(e))
                sys.exit(1)
        return YAMLHelper.cache[file]

    @staticmethod
    def analyse_keys(config_section, data_dict, expected_key_set):
        """
        Watch for dict key set differences
        :param config_section:
        :type config_section: str
        :param data_dict: data dictionary to check
        :type data_dict: dict
        :param expected_key_set: Expected set of key
        :type expected_key_set: set
        :raise: TypeError if key set is different than expected_key_set
        """
        diff = set(data_dict.keys()).difference(expected_key_set)
        if len(diff) != 0:
            raise TypeError(
                "Unrecognized {} key(s). {} should not contain other keys than {}.".format(
                    diff,
                    config_section,
                    expected_key_set,
                )
            )
