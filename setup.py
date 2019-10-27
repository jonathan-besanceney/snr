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
# This file is a part of save.
#
#    save is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    save is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with save.  If not, see <http://www.gnu.org/licenses/>.
# ------------------------------------------------------------------------------

from distutils.core import setup

setup(
    name='save',
    version='0.1',
    packages=['snr'],
    url='',
    license='LGPLv3',
    author='Jonathan Besanceney',
    author_email='jonathan.besanceney@gmail.com',
    description='Closure Tree implementation',
    install_requires=['PyYAML', 'PyInstaller', 'schedule'],
)
