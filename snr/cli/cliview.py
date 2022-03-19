# -*- coding: utf8 -*-
# ------------------------------------------------------------------------------
# Name:        cliview
# Purpose:     
#
#
# Author:      Jonathan Besanceney <jonathan.besanceney@gmail.com>
#
#
# Created:     27/10/2019
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


class CLIView:
    C_HEADER_APPS = "Application"
    C_HEADER_DATE = "Date"
    C_HEADER_STATUS = "Status"
    C_HEADER_FILES = "Files"
    C_HEADER_DB = "Databases"
    C_HEADER_COMMENTS = "Potential exclusions"
    C_SAVE_COLUMNS = [C_HEADER_APPS, C_HEADER_FILES, C_HEADER_DB, C_HEADER_COMMENTS]
    C_SAVE_HEADER = '{0:^{name_width}}\t{1:^{file_width}}\t{2:^{db_width}}\t{3:^{comment_width}}'
    C_SAVE_LINE = '{0:<{name_width}}\t{1:<{file_width}}\t{2:<{db_width}}\t{3:<{comment_width}}'
    C_RESTORE_COLUMNS = [C_HEADER_APPS, C_HEADER_DATE, C_HEADER_STATUS, C_HEADER_FILES, C_HEADER_DB, C_HEADER_COMMENTS]
    C_RESTORE_HEADER = '{0:^{name_width}}\t{1:^{date_width}}\t{2:^{status_width}}\t{3:^{file_width}}\t{4:^{db_width}}\t{5:^{comment_width}}'
    C_RESTORE_LINE = '{0:<{name_width}}\t{1:<{date_width}}\t{2:<{status_width}}\t{3:<{file_width}}\t{4:<{db_width}}\t{5:<{comment_width}}'

    @staticmethod
    def comment_width(saves, app_list):
        comment_width = 0
        for app in app_list:
            for date in saves[app].save_atoms:
                comment_width = max(
                    comment_width,
                    len('--exclude ')
                    + len(' '.join(['file:{}'.format(x) for x in saves[app].save_atoms[date].files]))
                    + 1
                    + len(' '.join(['database:{}'.format(x) for x in saves[app].save_atoms[date].databases]))
                )
        return comment_width

    @staticmethod
    def atom_list(saves, app_list):
        atom_list = list()
        for app in app_list:
            for date in saves[app].save_atoms:
                atom_list.append(saves[app].save_atoms[date])
        return atom_list

    @staticmethod
    def print_saveable_apps(saves):
        app_list = [x for x in saves.keys() if saves[x].saveable]
        print("Apps available for save: {}\n".format(', '.join(app_list)))

        atom_list = CLIView.atom_list(saves, app_list)
        if len(atom_list) == 0:
            print("No save done yet !")
        else:
            # get column width
            width = dict()
            width['name_width'] = max(max([len(x) for x in app_list]), len(CLIView.C_HEADER_APPS))
            width['file_width'] = max(max([len(', '.join(x.files)) for x in atom_list]), len(CLIView.C_HEADER_FILES))
            width['db_width'] = max(max([len(', '.join(x.databases)) for x in atom_list]), len(CLIView.C_HEADER_DB))
            width['comment_width'] = CLIView.comment_width(saves, app_list)

            # header
            print(CLIView.C_SAVE_HEADER.format(*CLIView.C_SAVE_COLUMNS, **width))
            # lines
            for name in app_list:
                save_atom = saves[name].save_atom
                comment = '--exclude ' + ' '.join(['file:{}'.format(x) for x in save_atom.files]) + ' ' + ' '.join(
                    ['database:{}'.format(x) for x in save_atom.databases])
                print(
                    CLIView.C_SAVE_LINE.format(
                        name,
                        ', '.join(save_atom.files),
                        ', '.join(save_atom.databases),
                        comment,
                        **width
                    )
                )

    @staticmethod
    def print_restoreable_apps(saves):
        app_list = [x for x in saves.keys() if saves[x].restoreable]
        atom_list = CLIView.atom_list(saves, app_list)

        # get column width
        width = dict()
        width['name_width'] = max(max([len(x) for x in app_list]), len(CLIView.C_HEADER_APPS))
        width['date_width'] = max(max([len(x.date) for x in atom_list]) + len(" (Default)"), len(CLIView.C_HEADER_DATE))
        width['status_width'] = max(max([len(x.status.value) for x in atom_list]), len(CLIView.C_HEADER_STATUS))
        width['file_width'] = max(max([len(x.print_files()) for x in atom_list]), len(CLIView.C_HEADER_FILES))
        width['db_width'] = max(max([len(x.print_databases()) for x in atom_list]), len(CLIView.C_HEADER_DB))
        width['comment_width'] = CLIView.comment_width(saves, app_list)
        # header
        print("Apps available for restore: {}\n".format(', '.join(app_list)))
        print(CLIView.C_RESTORE_HEADER.format(*CLIView.C_RESTORE_COLUMNS, **width))
        # lines
        for name in app_list:
            save_atoms = saves[name].save_atoms
            for atom in sorted(save_atoms.keys(), reverse=True):
                comment = '--exclude ' + ' '.join(
                    ['file:{}'.format(x) for x in save_atoms[atom].files]) + ' ' + ' '.join(
                    ['database:{}'.format(x) for x in save_atoms[atom].databases])
                print(
                    CLIView.C_RESTORE_LINE.format(
                        name,
                        save_atoms[atom].date + " (Default)"
                        if save_atoms[atom].date == saves[name].last_save.date
                        else save_atoms[atom].date,
                        save_atoms[atom].status.value,
                        save_atoms[atom].print_files(),
                        save_atoms[atom].print_databases(),
                        comment,
                        **width
                    )
                )
