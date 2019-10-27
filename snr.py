# -*- coding: utf8 -*-
# ------------------------------------------------------------------------------
# Name:        snr
# Purpose:     Save and Restore entry point
#
#
# Author:      Jonathan Besanceney <jonathan.besanceney@gmail.com>
#
#
# Created:     21/10/2019
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
import logging.config

from snr.log import Logger
from snr.yamlhelper import YAMLHelper
from snr.cli import CLI

C_YAML_LOG_BASIC = """
version: 1
disable_existing_loggers: False
formatters:
  simple:
    format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

handlers:
  console:
    class: logging.StreamHandler
    level: DEBUG
    formatter: simple
    stream: ext://sys.stdout

root:
  level: INFO
  handlers: [console]
        """
data = YAMLHelper.loads(C_YAML_LOG_BASIC)
logging.config.dictConfig(data)
logger = logging.getLogger(__name__)


if __name__ == '__main__':
    args = CLI.init()
    if os.path.exists(args.conf):
        logger = Logger(YAMLHelper.load(args.conf), __name__).get()
    args.func(args)  # call the default function
