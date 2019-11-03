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
    """

    C_YAML = """
database_helpers:
  postgres:
    env:
      PGPASSWORD: '$password'
    dump_command: [
      '/usr/bin/pg_dump',
      '--host=$host',
      '--port=$port',
      '--username=$username',
      '--clean',
      '--if-exists',
      '--dbname=$dbname'
      ]
    restore_command: [
      '/usr/bin/psql',
      '--host=$host',
      '--port=$port',
      '--username=$username',
      '$dbname'
    ]
    list_database_command: [
      '/usr/bin/psql',
      '--host=$host',
      '--port=$port',
      '--username=$username',
      '--tuples-only',
      '--command=SELECT datname FROM pg_database WHERE datname NOT IN (''postgres'', ''template1'', ''template0'');'
    ]
    create_database_command: [
      '/usr/bin/psql',
      '--host=$host',
      '--port=$port',
      '--username=$username',
      '--command=CREATE DATABASE $dbname WITH OWNER = postgres ENCODING = ''UTF8'' CONNECTION LIMIT = -1;'
    ]
    create_user_and_assign_command: [
      '/usr/bin/psql',
      '--host=$host',
      '--port=$port',
      '--username=$username',
      '--command=DO
      $do$
      BEGIN
        IF NOT EXISTS (
          SELECT
          FROM   pg_catalog.pg_roles
          WHERE  rolname = ''$user''
        ) THEN
          CREATE USER "$user" WITH LOGIN NOSUPERUSER INHERIT NOCREATEDB NOCREATEROLE NOREPLICATION;
          ALTER USER "$user" PASSWORD ''$passwd'';
        END IF;
      END
      $do$;
      ALTER DATABASE $dbname OWNER TO "$user";'
    ]
  mysql:
    env:
      MYSQL_PWD: '$password'
    dump_command: [
      '/usr/bin/mysqldump',
      '--host=$host',
      '--port=$port',
      '--user=$username',
      '--default-character-set=utf8',
      '$dbname'
      ]
    restore_command: [
      '/usr/bin/mysql',
      '--host=$host',
      '--port=$port',
      '--user=$username',
      '$dbname'
    ]
    list_database_command: [
      '/usr/bin/mysql',
      '--host=$host',
      '--port=$port',
      '--user=$username',
      '--execute=SELECT schema_name
        FROM information_schema.schemata
        WHERE schema_name NOT IN (''information_schema'', ''mysql'', ''performance_schema'', ''sys'');',
      '--batch',
      '--silent'
    ]
    create_database_command: [
      '/usr/bin/mysql',
      '--host=$host',
      '--port=$port',
      '--user=$username',
      '--execute=CREATE DATABASE $dbname CHARACTER SET utf8 COLLATE utf8_general_ci;'
    ]
    create_user_and_assign_command: [
      '/usr/bin/mysql',
      '--host=$host',
      '--port=$port',
      '--user=$username',
      '--execute=CREATE USER IF NOT EXISTS ''$user'' IDENTIFIED BY ''$passwd'';
        GRANT ALL PRIVILEGES ON $dbname.* TO ''$user'';
      '
    ]

databases:
  - instance: pg_instance
    type: postgres
    host: 192.168.1.123
    port: 5432
    credentials: /root/.pg_root
  - instance: my_instance
    type: mysql
    host: 192.168.1.124
    port: 3306
    credentials: /root/.my_root

    """

    HELPERS = 'database_helpers'
    HELPERS_KEYS = {'postgres', 'mysql'}

    H_ENV = 'env'
    H_DUMP = 'dump_command'
    H_RESTORE = 'restore_command'
    H_LIST_DB = 'list_database_command'
    H_CREATE_DB = 'create_database_command'
    H_CREATE_USER = 'create_user_and_assign_command'
    HELPER_KEYS = {H_RESTORE, H_DUMP, H_LIST_DB, H_CREATE_DB, H_CREATE_USER}
    HELPER_OPTIONAL_KEYS = {H_ENV}
    DBS = 'databases'
    D_INSTANCE = 'instance'
    D_TYPE = 'type'
    D_HOST = 'host'
    D_PORT = 'port'
    D_CREDS = 'credentials'
    D_INSTANCE_KEYS = {D_INSTANCE, D_TYPE, D_HOST, D_PORT, D_CREDS}
    C_USER = 'username'
    C_PASS = 'password'
    C_KEYS = {C_USER, C_PASS}

    def __init__(
            self, instance, db_type, host, port, credentials,
            dump_command, restore_command, list_databases_command, create_database_command,
            create_user_and_assign_command,
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
        self._create_user_and_assign_command = create_user_and_assign_command
        self._username = username
        self._password = password
        self._compression = compression
        self._env = env
        self._dump_process = None
        self._databases = list()

    @staticmethod
    def get_instances(conf):
        try:
            data = YAMLHelper.load(conf)

            # validate *helpers* keys
            YAMLHelper.analyse_keys(
                Database.HELPERS,
                data[Database.HELPERS],
                optional_key_set=Database.HELPERS_KEYS
            )

            helpers = dict()
            for db_type in data[Database.HELPERS]:
                # Validate helper configuration keys
                YAMLHelper.analyse_keys(
                    Database.HELPERS,
                    data[Database.HELPERS][db_type],
                    Database.HELPER_KEYS,
                    Database.HELPER_OPTIONAL_KEYS
                )

                helpers[db_type] = data[Database.HELPERS][db_type]

            databases = dict()
            for db in data[Database.DBS]:
                YAMLHelper.analyse_keys(Database.DBS, db, Database.D_INSTANCE_KEYS)

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
                    helpers[db[Database.D_TYPE]][Database.H_CREATE_USER],
                    username,
                    password,
                    Compression.get_instance(conf),
                    env
                )

            return databases
        except TypeError as e:
            logger.error("Database configuration error : {}".format(e))
        except IOError as e:
            logger.error("{}".format(e))

    def stop(self):
        if self._dump_process is None:
            logger.warning("Database save process is not running, can't kill it !")
            return
        if self._dump_process.returncode is not None:
            logger.warning("Database save process has already finished, can't kill it !")
            return
        logger.warning("Killing Database save process {}".format(self._dump_process.pid))
        self._dump_process.kill()

    def _prepare_command(self, command, dbname="", db_prefix="", user="", passwd=""):
        cmd = list()
        for arg in command:
            cmd.append(
                Template(arg).safe_substitute(
                    host=self._host,
                    port=self._port,
                    username=self._username,
                    password=self._password,
                    dbname="{}{}".format(db_prefix, dbname),
                    user=user,
                    passwd=passwd
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
                # mysql deletes MYSQL_PWD when terminate
                if env in os.environ.keys():
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

        try:
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
        except KeyboardInterrupt:
            logger.warning("Caught KeyboardInterrupt !")

    def restore(self, dbname, backup, db_prefix='', credentials=None):
        if '{}{}'.format(db_prefix, dbname) not in self.databases:
            logger.warning("Database {}{} does not exist. Trying to create it.".format(db_prefix, dbname))
            if not self.create_database(dbname, db_prefix):
                return

            if credentials:
                if not self.create_user(
                        credentials[Database.C_USER],
                        credentials[Database.C_PASS],
                        dbname,
                        db_prefix
                ):
                    return

        start = time.time()

        self._prepare_env()
        cmd = self._prepare_command(self._restore_command, dbname, db_prefix)
        try:
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
        except KeyboardInterrupt:
            logger.warning("Caught KeyboardInterrupt")

    def create_database(self, dbname, db_prefix=''):
        if '{}{}'.format(db_prefix, dbname) in self.databases:
            logger.error("Can't create database '{}{}'. This database already exist !".format(db_prefix, dbname))
            return False

        # reset db list
        self._databases = list()

        self._prepare_env()
        cmd = self._prepare_command(self._create_database_command, dbname, db_prefix)
        p = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        self._restore_env()

        if p.returncode == 0:
            logger.warning("Database '{}{}' created".format(db_prefix, dbname))
            return True
        else:
            logger.error(p.stderr.decode())
            return False

    def create_user(self, user, passwd, dbname, db_prefix=''):
        self._prepare_env()
        cmd = self._prepare_command(self._create_user_and_assign_command, dbname, db_prefix, user, passwd)
        p = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        self._restore_env()

        if p.returncode == 0:
            logger.warning("User '{}' created".format(user))
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
