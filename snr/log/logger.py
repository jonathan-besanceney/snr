# -*- coding: utf8 -*-
# ------------------------------------------------------------------------------
# Name:        logger
# Purpose:     
#
#
# Author:      Jonathan Besanceney <jonathan.besanceney@gmail.com>
#
#
# Created:     23/03/19
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
from os.path import join
import logging.config
import logging


class Logger:
    """
    Small logging wrapper helping configuration and reuse
    """
    DEFAULT_LEVEL = logging.INFO
    DEFAULT_CONFIG = """ 
logging:
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

    info_file_handler:
      class: logging.handlers.RotatingFileHandler
      level: INFO
      formatter: simple
      filename: info.log
      maxBytes: 10485760 # 10MB
      backupCount: 20
      encoding: utf8

    error_file_handler:
      class: logging.handlers.RotatingFileHandler
      level: ERROR
      formatter: simple
      filename: errors.log
      maxBytes: 10485760 # 10MB
      backupCount: 20
      encoding: utf8

  root:
    level: INFO
    handlers: [console, info_file_handler, error_file_handler]    
"""

    def __init__(self, config, name):
        """
        Setup logging configuration
        :param config: config dictionary
        :type config: Config
        :raise: TypeError if config is not Config instance
        """
        # check if logger is configured
        if not logging.root.handlers:
            logger = logging.getLogger(__name__)

            logger.info("Setting up default logger...")
            logging.basicConfig(level=Logger.DEFAULT_LEVEL)

            logger.info("Setting up logger for {}...".format(name))
            log_config = config["logging"]

            if 'log_path' in config:
                log_path = config["log_path"]

                log_config["handlers"]["info_file_handler"]["filename"] = join(
                    log_path, log_config["handlers"]["info_file_handler"]["filename"]
                )
                log_config["handlers"]["error_file_handler"]["filename"] = join(
                    log_path, log_config["handlers"]["error_file_handler"]["filename"]
                )

            logging.config.dictConfig(log_config)

        self._logger = logging.getLogger(name)

    def get(self):
        return self._logger

    @staticmethod
    def shutdown():
        logging.shutdown()
