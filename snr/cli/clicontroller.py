# -*- coding: utf8 -*-
# ------------------------------------------------------------------------------
# Name:        actions
# Purpose:     
#
#
# Author:      Jonathan Besanceney <jonathan.besanceney@gmail.com>
#
#
# Created:     26/10/2019
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
import sys
import logging

from snr.app import SaveAtom, AppSaveStatusEnum
from snr.cli.cliview import CLIView
from snr.save import Save

logger = logging.getLogger(__name__)


def check_conf(func):
    def wrapper(*args):
        arg = args[0]
        if not os.path.exists(arg.conf):
            logger.error(
                "Configuration file {} not found".format(arg.conf)
            )
            logger.error(
                "Please specify configuration path with --conf flag or generate configuration with genconf !"
            )
            sys.exit(1)
        try:
            func(*args)
        except Exception as e:
            logger.error("Unrecoverable error: {}. Terminating.".format(e))
            sys.exit(1)
        except KeyboardInterrupt:
            logger.warning("Caught KeyboardInterrupt! Trying to exit...")
            sys.exit(1)

    return wrapper


class CLIController:
    C_LOGGER_YAML = """
log_path: /var/log/save
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

    C_SYSTEMD_SERVICE_PATH = "/etc/systemd/system/snr.service"
    C_SYSTEMD_SERVICE = """
    [Unit]
    Description=Save and Restore Daemon
    Documentation=https://github.com/jonathan-besanceney/snr
    After=network-online.target

    [Service]
    ExecStart=/usr/bin/snr daemon
    Restart=always
    StartLimitInterval=0
    RestartSec=10

    [Install]
    WantedBy=multi-user.target
"""

    @staticmethod
    @check_conf
    def daemonize(args):
        logger.info("Starting SnR as daemon")
        Save.run_as_daemon(args.conf)

    @staticmethod
    def exclude(save_atom, excludes):
        """
        :param save_atom: save_atom to process
        :type save_atom: SaveAtom
        :param excludes: exclusion list
        :type excludes: list
        :return: processed save_atom
        :rtype: SaveAtom
        """
        try:
            if isinstance(excludes, str):
                excludes = list(excludes)
            for exclude in excludes:
                part, name = exclude.split(":")
                if save_atom.part_exists(part, name):
                    save_atom.del_part(part, name)
                else:
                    print("Unrecognized {}:{}. {} should be one of {}".format(part, name, part, SaveAtom.PART_TYPES))
                    sys.exit(1)
                print("Excluding {} {} !".format(part, name))
        except TypeError as e:
            print(e)
            sys.exit(1)
        return save_atom

    @staticmethod
    @check_conf
    def save(args):
        saves = Save.get_instances(args.conf)
        if args.app == "list":
            CLIView.print_saveable_apps(saves)
        else:
            if args.app not in saves.keys():
                print("{} is not a registered app that can be saved !\n".format(args.app))
                CLIView.print_saveable_apps(saves)
            else:
                save = saves[args.app]
                save_atom = save.save_atom
                if args.exclude:
                    save_atom = CLIController.exclude(save_atom, args.exclude)
                print("Start saving {}...".format(args.app))
                save.save(save_atom)

    @staticmethod
    @check_conf
    def restore(args):
        saves = Save.get_instances(args.conf)
        if args.app == "list":
            CLIView.print_restoreable_apps(saves)
        else:
            if args.app not in saves.keys():
                print("{} is not a registered app that can be restored !\n".format(args.app))
                CLIView.print_restoreable_apps(saves)
            else:
                save = saves[args.app]
                save_atom = save.last_save
                if args.date:
                    if args.date not in save.save_atoms.keys():
                        print(
                            "{} is not an available save date for {}. Choose one of {}".format(
                                args.date, args.app, ', '.join(sorted(save.save_atoms.keys(), reverse=True))
                            )
                        )
                        sys.exit(1)
                    save_atom = save.save_atoms[args.date]
                allow_partial = AppSaveStatusEnum.PARTIAL if args.allow_partial else AppSaveStatusEnum.FULL

                if args.exclude:
                    save_atom = CLIController.exclude(save_atom, args.exclude)
                print("Start restoring {}...".format(args.app))
                save.restore(save_atom=save_atom, allow_partial=allow_partial)

    @staticmethod
    def genconf(args):
        if os.path.exists(args.conf):
            print("{} already exists. Aborting sample configuration generation".format(args.conf))
            sys.exit(1)

        # create dir
        confdir = os.path.split(args.conf)[0]
        try:
            if not os.path.exists(confdir):
                os.makedirs(confdir)
            # append conf parts in conf file
            with open(args.conf, 'w') as f:
                # database conf
                from snr.database import Database
                f.write(Database.C_YAML)
                # compression conf
                from snr.compression import Compression
                f.write(Compression.C_YAML)
                # retention
                from snr.retention import Retention
                f.write(Retention.C_YAML)
                # app
                from snr.app import App
                f.write(App.C_YAML)
                # save
                from snr.save import Save
                f.write(Save.C_YAML)
                # logger
                f.write(CLIController.C_LOGGER_YAML)
            print("Sample configuration written in {}. You should edit it !".format(args.conf))
        except PermissionError as e:
            print("{}. Run as root if you intend to write in privileged folder".format(e))

    @staticmethod
    def create_systemd_service(args):
        try:
            if os.path.exists(CLIController.C_SYSTEMD_SERVICE_PATH):
                print("{} already exists. Aborting systemd service creation".format(CLIController.C_SYSTEMD_SERVICE_PATH))
                sys.exit(1)

            with open(CLIController.C_SYSTEMD_SERVICE_PATH, 'w') as f:
                f.write(CLIController.C_SYSTEMD_SERVICE)

            print(
                "Systemd service written in {} !".format(
                    CLIController.C_SYSTEMD_SERVICE_PATH
                )
            )
            print("Register service in boot with : systemctl daemon-reload && systemctl enable snr")
            print("Start with : systemctl start snr")
            print("Get current status with : systemctl status snr")
            print("Get logs with : journalctl -u snr -ef")
        except PermissionError as e:
            print("{}. Run as root if you intend to write in privileged folder".format(e))