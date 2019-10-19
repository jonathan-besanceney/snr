# -*- coding: utf8 -*-
# ------------------------------------------------------------------------------
# Name:        saveatom
# Purpose:     
#
#
# Author:      Jonathan Besanceney <jonathan.besanceney@gmail.com>
#
#
# Created:     22/09/2019
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
import os
import pprint
from enum import Enum
from pathlib import Path


class AppSaveStatusEnum(Enum):
    FULL = "Full"
    PARTIAL = "Partial"
    UNDEFINED = "Undefined"


class SaveAtom:
    def __init__(self, databases=None, files=None):
        self._date = None
        self._databases = dict()
        if databases:
            self.databases = databases
        self._databases_root_path = None
        self._files = dict()
        if files:
            self.files = files
        self._files_root_path = None
        self._status = AppSaveStatusEnum.UNDEFINED

    def clone(self):
        cloned = SaveAtom()
        cloned._date = self._date
        cloned._databases = self._databases
        cloned._files = self._files
        cloned._status = self._status
        return cloned

    @property
    def date(self):
        return self._date

    @date.setter
    def date(self, save_date):
        self._date = save_date

    def get_database(self, name):
        return self._databases[name]

    def set_database(self, name, item):
        self._status = AppSaveStatusEnum.UNDEFINED
        self._databases[name] = item
        if not self.databases_root_path:
            self.databases_root_path = str(Path(os.path.split(item)[0]).parent)

    def del_database(self, name):
        self._status = AppSaveStatusEnum.UNDEFINED
        if name in self._databases.keys():
            del self._databases[name]

    @property
    def databases(self):
        return list(self._databases.keys())

    @databases.setter
    def databases(self, dbs):
        self._status = AppSaveStatusEnum.UNDEFINED
        self._databases.update(dict((db, None) for db in dbs))

    @property
    def databases_root_path(self):
        return self._databases_root_path

    @databases_root_path.setter
    def databases_root_path(self, root_path):
        if self._databases_root_path != root_path:
            self._databases_root_path = root_path

    def get_file(self, name):
        return self._files[name]

    def set_file(self, name, item):
        self._status = AppSaveStatusEnum.UNDEFINED
        self._files[name] = item
        if not self._files_root_path:
            self.files_root_path = str(Path(os.path.split(item)[0]).parent)

    def del_file(self, name):
        self._status = AppSaveStatusEnum.UNDEFINED
        if name in self._files.keys():
            del self._files[name]

    @property
    def files(self):
        return list(self._files.keys())

    @files.setter
    def files(self, files):
        self._status = AppSaveStatusEnum.UNDEFINED
        self._files.update(dict((f, None) for f in files))

    @property
    def files_root_path(self):
        return self._files_root_path

    @files_root_path.setter
    def files_root_path(self, root_path):
        if self._files_root_path != root_path:
            self._files_root_path = root_path

    @property
    def status(self):
        """
        Contains save atom status. Status is computed if set to UNDEFINED.
        :rtype: AppSaveStatusEnum
        """
        if self._status == AppSaveStatusEnum.UNDEFINED:
            obj_count = len(self._databases.keys())
            obj_count += len(self._files.keys())
            blank_obj_count = len([blank_db for blank_db in self._databases.values() if blank_db is None])
            blank_obj_count += len([blank_file for blank_file in self._files.values() if blank_file is None])
            if blank_obj_count == 0:
                self._status = AppSaveStatusEnum.FULL
            elif 0 < blank_obj_count < obj_count:
                self._status = AppSaveStatusEnum.PARTIAL
            else:
                self._status = AppSaveStatusEnum.UNDEFINED
        return self._status

    def __repr__(self):
        pp = pprint.PrettyPrinter(indent=2)
        out = pp.pformat(
            {
                'date': self._date,
                'databases': self._databases,
                'databases_root_path': self._databases_root_path,
                'files': self._files,
                'files_root_path': self._files_root_path,
                'status': self.status.value
            }
        )
        return out
