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
import logging
import time
from threading import Thread

import schedule

from snr.app import App
from snr.app.saveatom import AppSaveStatusEnum
from snr.retention import Retention
from snr.yamlhelper import YAMLHelper

logger = logging.getLogger(__name__)


class Save(Thread):
    """

    """

    C_YAML = """
saves:
  - app_name: seafile
    destination: '/data/saves/$app/$type/$name/$name-$date'
    retention:
      databases: database_standard
      files: file_standard
    schedules:
      - every: 1
        interval: day
        at: "00:00"
  - app_name: gitlab
    destination: '/data/saves/$app/$type/$name/$name-$date'
    retention:
      databases: database_standard
      files: file_standard
    schedules:
      - every: 1
        interval: day
        at: "01:00"
  - app_name: seafile-test-restore
    destination: '/data/saves/seafile/$type/$name/$name-$date'
    allowed_actions:
      - restore
      #  save
  - app_name: gitlab-test-restore
    destination: '/data/saves/gitlab/$type/$name/$name-$date'
    allowed_actions:
      - restore
      #  save
"""

    C_SAVES = 'saves'
    C_SAVE_APP_NAME = 'app_name'
    C_SAVE_DEST = 'destination'
    C_SAVE_SCHEDS = 'schedules'
    C_SAVE_RETENTION = 'retention'
    C_SAVE_ALLOWED_ACTIONS = 'allowed_actions'
    C_SAVE_KEYS = {C_SAVE_APP_NAME}
    C_SAVE_OPT_KEYS = {C_SAVE_DEST, C_SAVE_SCHEDS, C_SAVE_RETENTION, C_SAVE_ALLOWED_ACTIONS}
    C_SAVE_SCHEDS_EVERY = 'every'
    C_SAVE_SCHEDS_INTERVAL = 'interval'
    C_SAVE_SCHEDS_INTERVAL_VALUES = {
        'second',
        'seconds',
        'minute',
        'minutes',
        'hour',
        'hours',
        'day',
        'days',
        'week',
        'weeks',
        'monday',
        'mondays',
        'tuesday',
        'tuesdays',
        'wednesday',
        'wednesdays',
        'thursday',
        'thursdays',
        'friday',
        'fridays',
        'saturday',
        'saturdays',
        'sunday',
        'sundays'
    }
    C_SAVE_SCHEDS_AT = 'at'
    C_SAVE_SCHEDS_KEYS = {C_SAVE_SCHEDS_EVERY, C_SAVE_SCHEDS_INTERVAL}
    C_SAVE_SCHEDS_KEYS_OPT = {C_SAVE_SCHEDS_AT}
    C_SAVE_RETENTION_DBS = 'databases'
    C_SAVE_RETENTION_FILES = 'files'
    C_SAVE_RETENTION_OPT_KEYS = {C_SAVE_RETENTION_DBS, C_SAVE_RETENTION_FILES}
    C_SAVE_ACTION_SAVE = 'save'
    C_SAVE_ACTION_RESTORE = 'restore'
    C_SAVE_ACTIONS = {C_SAVE_ACTION_SAVE, C_SAVE_ACTION_RESTORE}

    def __init__(self, name, destination, retentions, schedules, allowed_actions, app, conf):
        """

        :param name:
        :type name: str
        :param destination:
        :type destination: str
        :param retentions:
        :type retentions: dict
        :param schedules:
        :type schedules: dict
        :param allowed_action:
        :type allowed_action: list
        :param app: App
        :type app: App
        :param conf: conf file
        :type conf: str
        """
        super(Save, self).__init__()
        self._name = name

        self._destination = destination
        self._retentions = retentions
        self._schedules = schedules
        self._allowed_actions = allowed_actions
        self._app = app
        self._conf = conf
        self._run = True

    def run(self) -> None:
        if len(self._schedules) == 0:
            logger.info("No schedule defined for {}".format(self._name))
        else:
            logger.info("Starting schedule threads for {}...".format(self._name))
            for sched in self._schedules:
                job = schedule.every(sched[Save.C_SAVE_SCHEDS_EVERY])
                job = job.__getattribute__(sched[Save.C_SAVE_SCHEDS_INTERVAL])
                at = ""
                if Save.C_SAVE_SCHEDS_AT in sched.keys():
                    job = job.at(sched[Save.C_SAVE_SCHEDS_AT])
                    at = sched[Save.C_SAVE_SCHEDS_AT]
                job.do(self.save)
                logger.info(
                    "setting up {} save every {} {} {}".format(
                        self._name,
                        sched[Save.C_SAVE_SCHEDS_EVERY],
                        sched[Save.C_SAVE_SCHEDS_INTERVAL],
                        at
                    )
                )

            try:
                while self._run:
                    # Checks whether a scheduled task
                    # is pending to run or not
                    schedule.run_pending()
                    time.sleep(5)
            except KeyboardInterrupt:
                logger.warning("Caught KeyboardInterrupt")

            logger.info("Terminating schedule thread")

    def terminate(self):
        self._run = False

    @staticmethod
    def run_as_daemon(conf):
        saves = Save.get_instances(conf)
        try:
            for name in saves.keys():
                saves[name].start()
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            logger.warning("Caught KeyboardInterrupt")
        finally:
            for name in saves:
                saves[name].terminate()
            for name in saves:
                saves[name].join()

    @staticmethod
    def get_instances(conf):
        """
        Instanciate Save instances
        :param conf: yaml file path
        :type conf: str
        :return: dictionary of apps
        :rtype: dict
        """
        try:
            data = YAMLHelper.load(conf)
            app = App.get_instances(conf)
            if app is None:
                raise TypeError("Error getting apps")

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
                    for sched in save[Save.C_SAVE_SCHEDS]:
                        YAMLHelper.analyse_keys(
                            Save.C_SAVE_SCHEDS,
                            sched,
                            Save.C_SAVE_SCHEDS_KEYS,
                            Save.C_SAVE_SCHEDS_KEYS_OPT
                        )
                        YAMLHelper.check_key_values(
                            Save.C_SAVE_SCHEDS_INTERVAL,
                            sched[Save.C_SAVE_SCHEDS_INTERVAL],
                            Save.C_SAVE_SCHEDS_INTERVAL_VALUES
                        )
                    schedules = save[Save.C_SAVE_SCHEDS]

                allowed_actions = Save.C_SAVE_ACTIONS
                if Save.C_SAVE_ALLOWED_ACTIONS in save.keys():
                    YAMLHelper.check_key_values(
                        Save.C_SAVE_ALLOWED_ACTIONS,
                        save[Save.C_SAVE_ALLOWED_ACTIONS],
                        Save.C_SAVE_ACTIONS
                    )
                    allowed_actions = list()
                    for action in save[Save.C_SAVE_ALLOWED_ACTIONS]:
                        allowed_actions.append(action)
                saves[name] = Save(name, destination, retentions, schedules, allowed_actions, app[name], conf)

            return saves
        except TypeError as e:
            logger.error("Save configuration error : {}".format(e))
            raise e
        except IOError:
            logger.error("{} does not exist".format(conf))

    def save(self, save_atom=None):
        """
        Save.
        :param save_atom: Optional. Used to make partial save.
        :return: filled save_atom
        :rtype: snr.app.SaveAtom
        """
        if not self.restoreable:
            logger.error('{} has no save right !'.format(self._name))
            return

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
    def save_atom(self):
        """
        :return: save_atom
        :rtype: snr.app.SaveAtom
        """
        return self._app.save_atom

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
        if not self.restoreable:
            logger.error('{} has no restore right !'.format(self._name))
            return

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

    @property
    def saveable(self):
        if Save.C_SAVE_ACTION_SAVE in self._allowed_actions:
            return True
        return False

    @property
    def restoreable(self):
        if Save.C_SAVE_ACTION_RESTORE in self._allowed_actions:
            return True
        return False
