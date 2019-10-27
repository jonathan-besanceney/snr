# -*- coding: utf8 -*-
# ------------------------------------------------------------------------------
# Name:        cli
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
import argparse

from snr.cli.clicontroller import CLIController

if __name__ == '__main__':
    pass


class CLI:

    C_CONF_PATH = "/etc/snr/save.yaml"

    C_DAEMON = {
        'arg': 'daemon',        'help': 'Start snr as a daemon',
        'func': CLIController.daemonize,
        'opts': []
    }
    C_SAVE = {
        'arg': 'save',         'help': 'Save specified application. '
                                       'If not followed by --app, gives the list of app available for save',
        'func': CLIController.save,
        'opts': [
            {
                'args': ('-a', '--app'),
                'flags': {
                    'type': str,
                    'default': 'list',
                    'help': "Application to save. If not given display registered/save-able application list"
                }
            },
            {
                'args': ('-x', '--exclude'),
                'flags': {
                    'type': str,
                    'default': None,
                    'nargs': argparse.REMAINDER,
                    'help': 'Application parts to exclude from saving. Space separated list.'
                            ' Example: --exclude database:bd_name0 database:db_name1 file:file0 file:file1. '
                            'No exclusion per default'
                }
            }
        ]
    }
    C_RESTORE = {
        'arg': 'restore',      'help': 'Restore specified application.'
                                       'If not followed by --app, gives the list of app available for restore',
        'func': CLIController.restore,
        'opts': [
            {
                'args': ('-a', '--app'),
                'flags': {
                    'type': str,
                    'default': 'list',
                    'help': "Application to restore. If not given display registered/restore-able save-atom list"
                }
            },
            {
                'args': ('-d', '--date'),
                'flags': {
                    'type': str,
                    'default': None,
                    'help': 'Select date of the save atom to restore. Latest selected per default'
                }
            },
            {
                'args': ('-x', '--exclude'),
                'flags': {
                    'type': str,
                    'default': None,
                    'nargs': argparse.REMAINDER,
                    'help': 'Application parts to exclude from restoration. No exclusion per default'
                }
            },
            {
                'args': ('-p', '--allow-partial'),
                'flags': {
                    'action': 'store_true',
                    'help': 'Allow restoration of a partial save. Disabled per default'
                }
            }
        ]
    }
    C_GEN_CONFIG = {
        'arg': 'genconf',      'help': 'Generate sample configuration and exit',
        'func': CLIController.genconf,
        'opts': []
    }
    C_ACTIONS = [C_DAEMON, C_SAVE, C_RESTORE, C_GEN_CONFIG]

    @staticmethod
    def init():
        parser = argparse.ArgumentParser()
        parser.add_argument(
            '-c', '--conf',
            default=CLI.C_CONF_PATH,
            type=str,
            help='Specify configuration file. Defaults to {}'.format(CLI.C_CONF_PATH)
        )

        subparsers = parser.add_subparsers(prog="snr")

        for action in CLI.C_ACTIONS:
            sp = subparsers.add_parser(action['arg'], help=action['help'])
            for opt in action['opts']:
                sp.add_argument(*opt['args'], **opt['flags'])
            sp.set_defaults(func=action['func'])

        return parser.parse_args()
