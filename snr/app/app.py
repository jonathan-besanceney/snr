# -*- coding: utf8 -*-
# ------------------------------------------------------------------------------
# Name:        app
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
import re
import time
from datetime import datetime
import logging
import os
from string import Template
import functools
from threading import Thread

from snr.app.saveatom import SaveAtom, AppSaveStatusEnum
from snr.yamlhelper.yamlhelper import YAMLHelper
from snr.database.database import Database
from snr.compression.compression import Compression

logger = logging.getLogger(__name__)


class App:
    """
    App management
    """

    C_YAML = """
apps:
  - name: seafile
    databases:
      - name: ccnet
        databaseName: ccnet-db
        instance: my_instance
        credentials: /root/.seafile
      - name: seafile
        databaseName: seafile-db
        instance: my_instance
        credentials: /root/.seafile
      - name: seahub
        databaseName: seahub-db
        instance: my_instance
        credentials: /root/.seafile
    files:
        - name: data
          hostPath: /data/seafile
  - name: seafile-test-restore
    databases:
      - name: ccnet
        databasePrefix: restore_
        databaseName: ccnet
        instance: my_instance
        credentials: /root/.seafile
      - name: seafile
        databasePrefix: restore_
        databaseName: seafile
        instance: my_instance
        credentials: /root/.seafile
      - name: seahub
        databasePrefix: restore_
        databaseName: seahub
        instance: my_instance
        credentials: /root/.seafile
    files:
      - name: data
        hostPath: /data/seafile/restore/seafile
  - name: gitlab
    databases:
      - name: gitlab
        databaseName: gitlab
        instance: pg_instance
        credentials: /root/.gitlab
    files:
      - name: data
        hostPath: /data/gitlab
  - name: gitlab-test-restore
    databases:
      - name: gitlab
        databasePrefix: restore_
        databaseName: gitlab
        instance: pg_instance
        credentials: /root/.gitlab
    files:
      - name: data
        hostPath: /data/restore/gitlab
    """

    C_APPS = 'apps'
    C_NAME = 'name'
    C_DBS = 'databases'
    C_DB_NAME = 'name'
    C_DATABASE_PREFIX = 'databasePrefix'
    C_DATABASE_NAME = 'databaseName'
    C_DB_INSTANCE = 'instance'
    C_DB_KEYS = {C_DB_NAME, C_DATABASE_NAME, C_DB_INSTANCE}
    C_DB_OPTIONAL_KEYS = {C_DATABASE_PREFIX, Database.D_CREDS}

    C_FILES = 'files'
    C_FILE_NAME = 'name'
    C_FILE_PATH = 'hostPath'
    C_FILE_KEYS = {C_FILE_NAME, C_FILE_PATH}
    C_APP_KEYS = {C_NAME, C_DBS, C_FILES}
    C_DATE_FORMAT = '%Y-%m-%d-%H-%M'
    C_DATE_REGEX = re.compile(r'(\d\d\d\d-\d\d-\d\d-\d\d-\d\d)')

    STATUS = 'status'

    C_ALL = ('All', )

    def __init__(self, name, databases, files, compression):
        """
        :param name: app name
        :type name: str
        :param databases: database list
        :type databases: list
        :param files: file dictionary
        :type files: dict
        :param compression: Compression helper
        :type compression: Compression
        """
        self._name = name
        self._databases = databases
        self._files = files
        self._compression = compression

        db_names = list()
        for db in self._databases:
            db_names.append(db[App.C_DB_NAME])

        file_names = list()
        for file in self._files.keys():
            file_names.append(file)

        self._save_atom = SaveAtom(db_names, file_names)

    @staticmethod
    def get_instances(conf):
        try:
            data = YAMLHelper.load(conf)

            db_instances = Database.get_instances(conf)
            if db_instances is None:
                raise TypeError("Error getting databases.")
            compression = Compression.get_instance(conf)
            if compression is None:
                raise TypeError("Error getting compression object.")

            apps = dict()
            for app in data[App.C_APPS]:
                # an app may not contain database or file
                YAMLHelper.analyse_keys(App.C_APPS, app, optional_key_set=App.C_APP_KEYS)

                databases = list()
                # Do we have DB(s) to save
                if App.C_DBS in app and app[App.C_DBS]:
                    for db in app[App.C_DBS]:
                        YAMLHelper.analyse_keys(App.C_DBS, db, App.C_DB_KEYS, App.C_DB_OPTIONAL_KEYS)

                        db_prefix = ""
                        if App.C_DATABASE_PREFIX in db.keys():
                            db_prefix = db[App.C_DATABASE_PREFIX]
                        credentials = ""
                        if Database.D_CREDS in db.keys():
                            credentials = YAMLHelper.load(db[Database.D_CREDS])
                            YAMLHelper.analyse_keys(db[Database.D_CREDS], credentials, Database.C_KEYS)

                        databases.append(
                            {
                                App.C_DATABASE_PREFIX: db_prefix,
                                App.C_DB_NAME: db[App.C_DB_NAME],
                                App.C_DATABASE_NAME: db[App.C_DATABASE_NAME],
                                App.C_DB_INSTANCE: db_instances[db[App.C_DB_INSTANCE]],
                                Database.D_CREDS: credentials
                            }
                        )

                files = dict()
                # Do we have Files to save
                if App.C_FILES in app and app[App.C_FILES]:
                    for dirs in app[App.C_FILES]:
                        YAMLHelper.analyse_keys(App.C_FILES, dirs, App.C_FILE_KEYS)
                        files[dirs[App.C_FILE_NAME]] = dirs[App.C_FILE_PATH]

                apps[app[App.C_NAME]] = App(
                    app[App.C_NAME],
                    databases,
                    files,
                    compression
                )

            return apps
        except TypeError as e:
            logger.error("Cannot initialize {} app : {}".format(app['name'], e))
        except IOError as e:
            logger.error("{} does not exist".format(conf))

    def _format_destination(self, destination, save_type, name, file):
        today = datetime.today().strftime(App.C_DATE_FORMAT)
        return Template(destination).safe_substitute(
            app=self._name,
            type=save_type,
            name=name,
            save=file,
            date=today
        )

    @property
    def save_atom(self):
        return self._save_atom.clone()

    @staticmethod
    def get_file_creation_date(path):
        """
        Return file creation date
        *nixes does not store creation time. Thus, os.path.getctime() wont help
        :param path: file path. It should contains App.C_DATE_REGEX (App.C_DATE_FORMAT) pattern before extension
        :type path: str
        :rtype: str
        """
        file = os.path.split(path)[1]
        # select last match to deal with twisted file naming convention
        m = App.C_DATE_REGEX.search(file)
        if m:
            return m.groups()[-1]
        else:
            return

    def save(self, destination, save_atom=None):
        """

        :param destination: destination folder containing /$app/$type/$name/$name-$date wilcards
        :type destination: str
        :param save_atom: Optional, provide an alternate SaveAtom object to allow partial save process.
        :type save_atom: Union[SaveAtom|None]
        :return: SaveAtom instance filed with save files
        """
        if save_atom is None:
            save_atom = self.save_atom

        try:
            start = time.time()

            # don't start if we are at one second to the next minute to avoid time stamping issue for a complete save
            if datetime.today().second == 59:
                time.sleep(1.1)

            # file save
            file_threads = list()
            for file in self._files:
                if file in save_atom.files:
                    save_path = self._format_destination(destination, App.C_FILES, file, file)
                    save_atom.set_file(file, self._compression.get_file_with_compressed_extension(save_path))
                    compress = functools.partial(self._compression.compress, self._files[file], save_path)
                    t = Thread(target=compress, name=file)
                    t.start()
                    file_threads.append(t)
            # db save
            db_threads = list()
            for db in self._databases:
                if db[App.C_DB_NAME] in save_atom.databases:
                    save_path = self._format_destination(
                        destination, App.C_DBS, db[App.C_DB_NAME], db[App.C_DATABASE_NAME]
                    )
                    save_atom.set_database(
                        db[App.C_DB_NAME],
                        self._compression.get_file_with_compressed_from_pipe_ext(save_path)
                    )
                    save = functools.partial(
                        db[App.C_DB_INSTANCE].save,
                        db[App.C_DATABASE_NAME],
                        save_path,
                        self._get_database_attr(db, App.C_DATABASE_PREFIX)
                    )
                    t = Thread(target=save, name=db[App.C_DB_NAME])
                    t.start()
                    db_threads.append(t)
            if len(db_threads) + len(file_threads) == 0:
                logger.warning("Nothing to do !")
                return

            # wait for them
            for t in db_threads:
                t.join()
                # If save file does not exist, remove it from save_atom
                if not os.path.exists(save_atom.get_database(t.name)):
                    save_atom.set_database(t.name, None)
                elif save_atom.date is None:
                    save_atom.date = App.get_file_creation_date(save_atom.get_database(t.name))
            for t in file_threads:
                t.join()
                # If save file does not exist, remove it from save_atom
                if not os.path.exists(save_atom.get_file(t.name)):
                    save_atom.set_file(t.name, None)

        except KeyboardInterrupt:
            logger.warning("User interruption, trying to kill remaining processes")
            raise

        logger.info("finished {} save in {}s".format(self._name, time.time()-start))
        return save_atom

    def _update_save_atoms(self, source, save_type, name, save_atoms):
        path = os.path.split(self._format_destination(source, save_type, name, name))[0]
        if os.path.exists(path):
            for f in os.listdir(path):
                full_path = os.path.join(path, f)
                file_date = App.get_file_creation_date(full_path)
                if file_date:
                    if file_date not in save_atoms.keys():
                        save_atoms[file_date] = self._save_atom.clone()
                    if not save_atoms[file_date].date:
                        save_atoms[file_date].date = file_date

                    if save_type == App.C_DBS:
                        save_atoms[file_date].set_database(name, full_path)
                    elif save_type == App.C_FILES:
                        save_atoms[file_date].set_file(name, full_path)

        return save_atoms

    def get_saves(self, source):
        """
        List all saves for this app from source path. Returns a dictionary organized by date (in str).
        See C_DATE_FORMAT for dictionary keys generation.
        :param source: source path with wilcards, as used in save()
        :type source: str
        :return: SaveAtom dictionary.
        :rtype: dict
        """
        save_atoms = dict()

        for db in self._databases:
            save_atoms = self._update_save_atoms(source, App.C_DBS, db[App.C_DB_NAME], save_atoms)

        for file in self._files:
            save_atoms = self._update_save_atoms(source, App.C_FILES, file, save_atoms)

        return save_atoms

    def _compare_file_list(self, file_list):
        """
        Compare provided file_list with current file list associated with this app.
        Incomplete file_list is allowed.
        :param file_list: list of file name to check
        :type file_list: list
        :return: True if list corresponds
        :rtype: bool
        """
        app_db_list = set(self._files.keys())
        diff = set(file_list).difference(app_db_list)
        if len(diff) > 0:
            logger.error(
                "Provided file set to restore {} does not corresponds to this app file set {}".format(
                    file_list,
                    app_db_list
                )
            )
            return False
        return True

    def _compare_db_list(self, db_list):
        """
        Compare provided db_list with current database list associated with this app.
        Incomplete db_list is allowed.
        :param db_list: list of db name to check
        :type db_list: list
        :return: True if list corresponds
        :rtype: bool
        """
        app_dbs = set()
        for d in self._databases:
            app_dbs.add(d[App.C_DATABASE_NAME])

        diff = set(db_list).difference(app_dbs)
        if len(diff) > 0:
            logger.error(
                "Provided database set to restore {} does not corresponds to this app database set {}".format(
                    db_list,
                    app_dbs
                )
            )
            return False
        return True

    def _get_database_attr(self, db_name, attr):
        """
        Returns Database attribute corresponding to db_name
        :param db_name: name of the db from which get attribute
        :type db_name: str
        :return: attr
        :rtype: Union[Database|str]
        """
        db_attr = ""
        for db in self._databases:
            if db_name == db[App.C_DATABASE_NAME]:
                db_attr = db[attr]

        return db_attr

    def restore(self, save_atom, allow_status=AppSaveStatusEnum.FULL):
        """

        :param save_atom: SaveAtom instance containing save files path
        :type save_atom: SaveAtom
        :param allow_status: Optional. Default FULL. If set to AppSaveStatusEnum.PARTIAL, allows restoration from
        a partial save.
        :type allow_status: AppSaveStatusEnum
        :return:
        """
        start = time.time()
        if save_atom.status == AppSaveStatusEnum.UNDEFINED:
            logger.error("restore({}) : Save atom is undefined !")
        if save_atom.status != AppSaveStatusEnum.FULL and save_atom.status != allow_status:
            logger.error(
                "restore({}) : The selected save is {}, you must set allow_status=AppSaveStatusEnum.PARTIAL to allow a restore.".format(
                    save_atom, save_atom.status
                )
            )
            return

        if not self._compare_file_list(save_atom.files):
            return

        if not self._compare_db_list(save_atom.databases):
            return

        threads = list()
        # file restore
        for f in save_atom.files:
            # avoid null file path
            if save_atom.get_file(f):
                decompress = functools.partial(self._compression.decompress, save_atom.get_file(f), self._files[f])
                t = Thread(target=decompress, name=f)
                t.start()
                threads.append(t)

        # database restore
        for d in save_atom.databases:
            db_instance = self._get_database_attr(d, App.C_DB_INSTANCE)
            restore = functools.partial(
                db_instance.restore,
                d,
                save_atom.get_database(d),
                self._get_database_attr(d, App.C_DATABASE_PREFIX),
                self._get_database_attr(d, Database.D_CREDS)
            )
            t = Thread(target=restore, name=d)
            t.start()
            threads.append(t)

        if len(threads) == 0:
            logger.warning("Nothing to do !")
        else:
            try:
                # wait for them
                for t in threads:
                    t.join()
                logger.info("finished {} restore in {}s".format(self._name, time.time() - start))
            except KeyboardInterrupt:
                logger.warning("User interruption, trying to kill remaining processes")
                raise
