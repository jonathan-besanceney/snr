# -*- coding: utf8 -*-
# ------------------------------------------------------------------------------
# Name:        setup
# Purpose:     Setup Script
#
#
# Author:      Jonathan Besanceney <jonathan.besanceney@gmail.com>
#
#
# Created:     2019
# Copyright:   (c) 2019
#
# Licence:     LGPLv3 2019.
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
from setuptools import setup

with open("README.md", 'r') as f:
    long_description = f.read()

setup(
    name='snr',
    version='1.06',
    packages=['snr', 'snr.app', 'snr.cli', 'snr.log', 'snr.save', 'snr.database', 'snr.retention', 'snr.yamlhelper',
              'snr.compression', 'snr.units'],
    url='https://***REMOVED***/gitlab/kubernetes/snr',
    long_description=long_description,
    license='LGPLv3',
    author='Jonathan Besanceney',
    author_email='jonathan.besanceney@gmail.com',
    description='Save and Restore utility',
    install_requires=['PyYAML', 'schedule'],
    entry_points={
        'console_scripts': [
            'snr = snr.cli.cli:main',
        ],
    }
)
