# -*- coding: utf8 -*-
# ------------------------------------------------------------------------------
# Name:        database
# Purpose:     Database save and restore. Configured through yaml config file
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
from string import Template
import time
import logging
import subprocess
import os

from snr.yamlhelper.yamlhelper import YAMLHelper
from snr.compression.compression import Compression
logger = logging.getLogger(__name__)


class Database:
    """
    Database save and restore helper factory.
    Configured through yaml config file via database_helpers and databases keyword :

    database_helpers:
      postgres:
        env:
          PGPASSWORD: '$password'
        dump_command: [
          '/usr/bin/pg_dump',
          '--host=$host',
          '--port=$port',
          '--username=$username',
          '--dbname=$dbname'
          ]
        restore_command: [
          '/usr/bin/psql',
          '--host=$host',
          '--port=$port',
          '--username=$username',
          '$dbname'
        ]
        create_database_command: [
          '/usr/bin/psql',
          '--host=$host',
          '--port=$port',
          '--username=$username',
          'CREATE DATABASE ...;'
        ]
      [...]

    databases:
      - instance: pg_bubblebox
        type: postgres
        host: 192.168.1.2
        port: 5432
        credentials: /home/jonathan/.pg_root
        [...]

    """
    HELPERS = 'database_helpers'
    H_ENV = 'env'
    H_DUMP = 'dump_command'
    H_RESTORE = 'restore_command'
    H_LIST_DB = 'list_database_command'
    H_CREATE_DB = 'create_database_command'
    HELPER_KEYS = {H_ENV, H_RESTORE, H_DUMP, H_LIST_DB, H_CREATE_DB}
    DBS = 'databases'
    D_INSTANCE = 'instance'
    D_TYPE = 'type'
    D_HOST = 'host'
    D_PORT = 'port'
    D_CREDS = 'credentials'
    DB_KEYS = {D_INSTANCE, D_TYPE, D_HOST, D_PORT, D_CREDS}
    C_USER = 'username'
    C_PASS = 'password'
    C_KEYS = {C_USER, C_PASS}

    def __init__(
            self, instance, db_type, host, port, credentials,
            dump_command, restore_command, list_databases_command, create_database_command,
            username, password,
            compression, env=None
    ):
        self._instance = instance
        self._type = db_type
        self._host = host
        self._port = port
        self._credentials = credentials
        self._dump_command = dump_command
        self._restore_command = restore_command
        self._list_databases_command = list_databases_command
        self._create_database_command = create_database_command
        self._username = username
        self._password = password
        self._compression = compression
        self._env = env
        self._dump_process = None
        self._databases = list()

    @staticmethod
    def get_databases(conf):
        try:
            data = YAMLHelper.load(conf)

            helpers = dict()
            for db_type in data[Database.HELPERS]:
                # Validate configuration keys
                YAMLHelper.analyse_keys(Database.HELPERS, data[Database.HELPERS][db_type], Database.HELPER_KEYS)

                helpers[db_type] = data[Database.HELPERS][db_type]

            databases = dict()
            for db in data[Database.DBS]:
                YAMLHelper.analyse_keys(Database.DBS, db, Database.DB_KEYS)

                env = None
                if Database.H_ENV in helpers[db[Database.D_TYPE]].keys():
                    env = helpers[db[Database.D_TYPE]][Database.H_ENV]

                creds = YAMLHelper.load(db[Database.D_CREDS])
                YAMLHelper.analyse_keys(db[Database.D_CREDS], creds, Database.C_KEYS)

                username = creds[Database.C_USER]
                password = creds[Database.C_PASS]

                databases[db[Database.D_INSTANCE]] = Database(
                    db[Database.D_INSTANCE],
                    db[Database.D_TYPE],
                    db[Database.D_HOST],
                    db[Database.D_PORT],
                    db[Database.D_CREDS],
                    helpers[db[Database.D_TYPE]][Database.H_DUMP],
                    helpers[db[Database.D_TYPE]][Database.H_RESTORE],
                    helpers[db[Database.D_TYPE]][Database.H_LIST_DB],
                    helpers[db[Database.D_TYPE]][Database.H_CREATE_DB],
                    username,
                    password,
                    Compression.get_compression(conf),
                    env
                )

            return databases
        except TypeError as e:
            logger.error("Database configuration error : {}".format(e))
        except IOError:
            logger.error("{} does not exist".format(conf))

    def stop(self):
        if self._dump_process is None:
            logger.warning("Database save process is not running, can't kill it !")
            return
        if self._dump_process.returncode is not None:
            logger.warning("Database save process has already finished, can't kill it !")
            return
        logger.warning("Killing Database save process {}".format(self._dump_process.pid))
        self._dump_process.kill()

    def _prepare_command(self, command, dbname="", db_prefix=""):
        cmd = list()
        for arg in command:
            cmd.append(
                Template(arg).safe_substitute(
                    host=self._host,
                    port=self._port,
                    username=self._username,
                    password=self._password,
                    dbname="{}{}".format(db_prefix, dbname)
                )
            )
        return cmd

    def _prepare_env(self):
        env_list = list()
        if self._env:
            for env in self._env.keys():
                env_list.append(env)
                os.environ[env] = Template(self._env[env]).safe_substitute(password=self._password)

    def _restore_env(self):
        if self._env:
            for env in self._env.keys():
                del os.environ[env]

    def save(self, dbname, file, db_prefix=""):
        if '{}{}'.format(db_prefix, dbname) not in self.databases:
            logger.error("Can't save database '{}'. This database does not exist !".format(dbname))
            return

        start = time.time()

        # add env var
        self._prepare_env()
        # prepare command
        cmd = self._prepare_command(self._dump_command, dbname)

        logger.info("starting {}".format(cmd))

        self._dump_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self._compression.compress_from_pipe(self._dump_process.stdout, file)
        if not self._dump_process.stdout.closed:
            self._dump_process.stdout.close()

        # remove env var
        self._restore_env()

        self._dump_process.wait()
        if self._dump_process.returncode == 0:
            logger.info("dumped {} in {:f}".format(dbname, time.time() - start))
        else:
            logger.error("Database dump ended with exit code {}".format(self._dump_process.returncode))
            if not self._dump_process.stderr.closed:
                logger.error(self._dump_process.stderr.read().decode())

        if not self._dump_process.stderr.closed:
            self._dump_process.stderr.close()

    def restore(self, dbname, backup, db_prefix=''):
        if '{}{}'.format(db_prefix, dbname) not in self.databases:
            logger.warning("Database {}{} does not exist. Trying to create it.".format(db_prefix, dbname))
            if not self.create_database('{}{}'.format(db_prefix, dbname)):
                return

        start = time.time()

        self._prepare_env()
        cmd = self._prepare_command(self._restore_command, dbname, db_prefix)

        logger.info("starting {}".format(cmd))
        extract_process = self._compression.decompress_to_pipe(backup)
        with extract_process.stdout as f:
            restore_process = subprocess.Popen(cmd, stdin=f, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _, err = restore_process.communicate()

        self._restore_env()

        if restore_process.returncode == 0:
            if len(err) != 0:
                logger.warning(err.decode().replace('\n', ''))

            logger.info("restored {}{} in {:f}".format(db_prefix, dbname, time.time() - start))

        else:
            logger.error(err.decode())

    def create_database(self, dbname, db_prefix=''):
        if dbname in self.databases:
            logger.error("Can't create database '{}'. This database already exist !".format(dbname))
            return False

        # reset db list
        self._databases = list()

        self._prepare_env()
        cmd = self._prepare_command(self._create_database_command, dbname, db_prefix)
        p = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        self._restore_env()

        if p.returncode == 0:
            logger.warning("Database '{}' created".format(dbname))
            return True
        else:
            logger.error(p.stderr.decode())
            return False

    @property
    def databases(self):
        if len(self._databases) == 0:
            self._prepare_env()
            cmd = self._prepare_command(self._list_databases_command)
            p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            self._restore_env()

            if p.returncode == 0:
                for db in p.stdout.decode().splitlines():
                    db = db.strip()
                    if len(db) > 0:
                        self._databases.append(db)

        return self._databases
