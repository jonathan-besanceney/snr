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
import sys
import logging
from yaml import load, dump, YAMLError
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper
from yaml.parser import ParserError

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

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
            except (ParserError, YAMLError, FileNotFoundError, IOError) as e:
                logger.error("Aborting : {}".format(e))
                raise e
        return YAMLHelper.cache[file]

    @staticmethod
    def loads(s):
        fd = StringIO(s)
        data = load(fd, Loader=Loader)
        return data


    @staticmethod
    def dump(obj):
        return dump(obj, Dumper=Dumper)

    @staticmethod
    def analyse_keys(config_section, data_dict, mandatory_key_set={}, optional_key_set={}):
        """
        Watch for dict key set differences
        :param config_section:
        :type config_section: str
        :param data_dict: data dictionary to check
        :type data_dict: dict
        :param mandatory_key_set: Mandatory set of key
        :type mandatory_key_set: set
        :param optional_key_set: Expected set of key. Must contain all keys, even optionals
        :type optional_key_set: set
        :raise: TypeError if key set is different than expected_key_set and if not all mandatory_key_set are in
        """
        key_set = set(data_dict.keys())
        err = ""

        if len(mandatory_key_set) > 0:
            got_key_set = key_set.difference(optional_key_set)
            diff = mandatory_key_set.difference(got_key_set)
            if len(diff) != 0:
                err = "Missing mandatory {} key(s). Mandatory keys in {} are {}.".format(
                        diff,
                        config_section,
                        mandatory_key_set
                    )
                # look deeper in case there is a typo
                diff = got_key_set.difference(mandatory_key_set)
                if len(diff) != 0:
                    err += "Unrecognized {} key(s). Mandatory keys in {} are {}.".format(
                            diff,
                            config_section,
                            mandatory_key_set
                        )

            # removes mandatory keys
            key_set = key_set.difference(mandatory_key_set)

        if len(optional_key_set) > 0:
            diff = key_set.difference(optional_key_set)
            if len(diff) != 0:
                err += "Unrecognized {} key(s). Optional keys in {} should not contain other keys than {}.".format(
                    diff,
                    config_section,
                    optional_key_set,
                )

        if len(err) > 0:
            raise TypeError(err)

    @staticmethod
    def check_key_values(key, value, value_set):
        if isinstance(value, list) or isinstance(value, set):
            for v in value:
                YAMLHelper.check_key_values(key, v, value_set)
        else:
            if value not in value_set:
                err = "Unrecognized value {} in key {}. Should contains one of {}".format(
                        value,
                        key,
                        value_set
                    )
                raise TypeError(err)
