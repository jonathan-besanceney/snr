# -*- coding: utf8 -*-
# ------------------------------------------------------------------------------
# Name:        save
# Purpose:     
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
import logging
import time

from snr.app import App
from snr.app.saveatom import AppSaveStatusEnum
from snr.retention import Retention
from snr.yamlhelper import YAMLHelper

logger = logging.getLogger(__name__)


class Save:
    """

    """

    C_YAML = """
saves:
  - name: seafile
    destination: '/mnt/saves/$app/$type/$name/$name-$date'
    retention:
      database: database_standard
      file: file_standard
    schedules:
      daily:
        hour: "00:00"
  - name: gitlab
    destination: '/mnt/saves/$app/$type/$name/$name-$date'
    retention:
      database: database_standard
      file: file_standard
    schedules:
      daily:
        hour: "00:00"
"""
    C_SAVES = 'saves'
    C_SAVE_APP_NAME = 'app_name'
    C_SAVE_DEST = 'destination'
    C_SAVE_SCHEDS = 'schedules'
    C_SAVE_RETENTION = 'retention'
    C_SAVE_KEYS = {C_SAVE_APP_NAME}
    C_SAVE_OPT_KEYS = {C_SAVE_DEST, C_SAVE_SCHEDS, C_SAVE_RETENTION}
    C_SAVE_SCHEDS_PERIOD = {'daily', 'weekly', 'monthly', 'quarterly', 'yearly'}
    C_SAVE_SCHEDS_PERIOD_HOUR = 'hour'
    C_SAVE_RETENTION_DBS = 'databases'
    C_SAVE_RETENTION_FILES = 'files'
    C_SAVE_RETENTION_OPT_KEYS = {C_SAVE_RETENTION_DBS, C_SAVE_RETENTION_FILES}

    def __init__(self, name, destination, retentions, schedules, app, daemon, conf):
        """

        :param name:
        :type name: str
        :param destination:
        :type destination: str
        :param retentions:
        :type retentions: dict
        :param schedules:
        :type schedules: dict
        :param app: App
        :type app: App
        :param daemon: if true makes app run in a thread and wake up at scheduled events
        :type daemon: bool
        :param conf: conf file
        :type conf: str
        """
        self._name = name

        self._destination = destination
        self._retentions = retentions
        self._schedules = schedules
        self._app = app
        self._daemon = daemon
        self._conf = conf

    @staticmethod
    def get_instances(conf, daemon):
        """
        Instanciate Save instances
        :param conf: yaml file path
        :type conf: str
        :param daemon: Ask to daemonize save
        :type daemon: bool
        :return: dictionary of apps
        :rtype: dict
        """
        try:
            data = YAMLHelper.load(conf)
            app = App.get_instances(conf)
            saves = dict()
            for save in data[Save.C_SAVES]:
                YAMLHelper.analyse_keys(Save.C_SAVES, save, Save.C_SAVE_KEYS, Save.C_SAVE_OPT_KEYS)
                name = save[Save.C_SAVE_APP_NAME]
                destination = None
                if Save.C_SAVE_DEST in save.keys():
                    destination = save[Save.C_SAVE_DEST]
                retentions = dict()
                if Save.C_SAVE_RETENTION in save.keys():
                    YAMLHelper.analyse_keys(
                        Save.C_SAVE_RETENTION,
                        save[Save.C_SAVE_RETENTION],
                        optional_key_set=Save.C_SAVE_RETENTION_OPT_KEYS
                    )
                    retentions = save[Save.C_SAVE_RETENTION]
                schedules = dict()
                if Save.C_SAVE_SCHEDS in save.keys():
                    YAMLHelper.analyse_keys(
                        Save.C_SAVE_SCHEDS,
                        save[Save.C_SAVE_SCHEDS],
                        optional_key_set=Save.C_SAVE_SCHEDS_PERIOD
                    )
                    schedules = save[Save.C_SAVE_SCHEDS]

                saves[name] = Save(name, destination, retentions, schedules, app[name], daemon, conf)

            return saves
        except TypeError as e:
            logger.error("Save configuration error : {}".format(e))
        except IOError:
            logger.error("{} does not exist".format(conf))

    def save(self, save_atom=None):
        """
        Save.
        :param save_atom: Optional. Used to make partial save.
        :return: filled save_atom
        :rtype: snr.app.SaveAtom
        """
        start = time.time()
        # Get default save_atom if none set
        if save_atom is None:
            save_atom = self._app.save_atom

        save_atom = self._app.save(self._destination, save_atom)

        if len(self._retentions) > 0:
            if Save.C_SAVE_RETENTION_DBS in self._retentions.keys() and save_atom.databases_root_path:
                dbs_retention = Retention.get_instance(self._conf, self._retentions[Save.C_SAVE_RETENTION_DBS])
                dbs_retention.run(save_atom.databases_root_path)

            if Save.C_SAVE_RETENTION_FILES in self._retentions.keys() and save_atom.files_root_path:
                files_retention = Retention.get_instance(self._conf, self._retentions[Save.C_SAVE_RETENTION_FILES])
                files_retention.run(save_atom.files_root_path)

        logger.info("{} save done in {}s".format(self._name, time.time()-start))
        if save_atom.status != AppSaveStatusEnum.FULL:
            logger.warning("{} save is {}".format(self._name, save_atom.status))
        else:
            logger.info("{} save is {}".format(self._name, save_atom.status))
        return save_atom

    @property
    def save_atoms(self):
        """
        :return: save dict
        :rtype: dict
        """
        return self._app.get_saves(self._destination)

    @property
    def last_save(self):
        """
        save atom
        :return: last available save_atom
        :rtype: snr.app.SaveAtom
        """
        save_atoms = self.save_atoms
        if len(save_atoms) > 0:
            return save_atoms[sorted(save_atoms.keys(), reverse=True)[0]]
        return None

    def restore(self, save_atom=None, date=None, allow_partial=AppSaveStatusEnum.FULL):
        """
        Restoration.
        :param save_atom: Optional. Specify save_atom to restore
        :type save_atom: snr.app.SaveAtom
        :param date: Optional. Specify save date
        :type date: str
        :param allow_partial: Optional. Allow restoration of a partial save. FULL per default.
        :type allow_partial: snr.app.AppSaveStatusEnum
        """
        if save_atom is None and date is None:
            save_atom = self.last_save
            if save_atom is None:
                logger.error("I have nothing to restore !")
                return

        if date is not None and save_atom is None:
            if date not in self.save_atoms.keys():
                logger.error(
                    "You picked up a wrong save date {}. Valid one are {}".format(date, self.save_atoms.keys())
                )
                return
            else:
                save_atom = self.save_atoms[date]

        self._app.restore(save_atom, allow_partial)
