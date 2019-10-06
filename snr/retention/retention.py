# -*- coding: utf8 -*-
# ------------------------------------------------------------------------------
# Name:        retention
# Purpose:     save retention
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

import os
import sys
from datetime import timedelta, datetime
from enum import Enum


class PeriodDuration(Enum):
    DAY = 1
    WEEK = 7
    MONTH = 28
    QUARTER = 91
    YEAR = 365


class Period:
    """
    Period definition.
    """

    def __init__(self, start, duration, latest=False):
        """
        :param start: datetime for the day
        :type start: datetime.datetime
        :param duration: number of days of this Period
        :type duration: PeriodDuration
        :param latest: optional. Select earliest per default, except for one day duration
        :type latest: bool
        """
        self._start = start
        self._duration = duration
        self._latest = latest

        if self._duration == 1:
            self._latest = True
        self._end = start - timedelta(days=duration.value)
        print("Période de {} jour(s) initialisée du {} au {}. Sélectionne le fichier le plus récent {}".format(duration, start, self._end, self._latest))

    @property
    def start(self):
        return self._start

    @property
    def end(self):
        return self._end

    @property
    def duration(self):
        return self._duration

    @property
    def latest(self):
        return self._latest

    def __repr__(self):
        return "Period(duration={}, start={}, end={}, latest={})".format(
            self._duration,
            self._start,
            self._end,
            self._latest
        )

    def get_matching_file(self, file_list):
        """
        Select oldest file in the list unless self._latest is set to False
        :type file_list: list
        :rtype: str()
        """

        # initialisation de la date pour la sélection du fichier, pour comprendre la construction voir
        # http://docs.python.org/3.3/faq/programming.html#is-there-an-equivalent-of-c-s-ternary-operator
        selected_date = self._end if self._latest else self._start
        selected_file = ""

        for file in file_list: #TODO : finaliser l'implémentation
            # TODO : move os.path.getctime to _make_file_list and make file_dict instead of file_list to store creation date in value
            file_date = datetime.fromtimestamp(os.path.getctime(file))

            # si la date de création du fichier est dans la période définie
            if self._start >= file_date >= self._end:
                # select_lastest = true
                if self._latest and selected_date < file_date:
                    selected_date = file_date
                    selected_file = file
                elif not self._latest and selected_date > file_date:
                    selected_date = file_date
                    selected_file = file

        if selected_file != "":
            print("Période de {} jour(s), Ce fichier est cool {} ! ".format(self._duration, selected_file))
        else:
            print("Période de {} jour(s), J'AI RIEN TROUVE ! ".format(self._duration))

        return selected_file


class Periods:
    """Classe permettant de définir des périodes de rétentions. Toujours sur la même durée.
    Chaque période cherche si possible à satisfaire sa contrainte en sélectionnant 
    le fichier le plus ancien disponible. Voir Period pour l'implémentation."""

    def __init__(self, period_length, number_of_period):
        """Instancie la classe à partir de la durée de la période en jours (int()) et du nombre de périodes 
        à générer"""

        self._period_length = period_length
        self._number_of_period = number_of_period
        self._period_list = list()

        #génère le nombre de périodes.
        period_start = datetime.today()
        i = 0
        while i < self._number_of_period:
            p_instance = Period(period_start, self._period_length)
            self._period_list.append(p_instance)
            period_start = p_instance.end
            i += 1

    def get_matching_files_list(self, file_list):
        """ A partir de la liste de fichier fourni, retourne les éléments retenus pour chaque Period.
        @param list()
        @return list()"""

        selected_file_list = list()

        for p in self._period_list:
            selected_file = p.get_matching_file(file_list)
            if selected_file != "":
                selected_file_list.append(selected_file)

        return selected_file_list


class Retention:
    """Classe de gestion de la rétention des fichiers de sauvegarde.

    Permet un paramétrage de rétention par :
    - les derniers jours (last_days) soit : conserve une sauvegarde par jour pendant nb * 1j
    - les dernières semaines (last_week) : conserve une sauvegarde par semaine pendant nb * 7j
    - les derniers mois (last_month) : conserve une sauvegarde par mois pendant nb * 28j 
    - les derniers trimestres (last_quarter) conserve une sauvegarde par trimestre pendant nb * 91j (soit 365/4)
    - les dernières années (last_year) : conserve une sauvegarde par année pendant nb * 365j
    Voir la classe Period pour l'implémentation de la sélection des fichiers à conserver"""

    def __init__(self):
        """Constructeur standard. Si utilisé, les paramètres de rétention suivant
        seront appliqués :
        5 derniers jours conservés
        1 sauvegarde pour la semaine
        Ne conserve pas de sauvegarde pour le mois
        1 sauvegarde pour le trimestre
        1 sauvegarde pour l'année"""

        self.__init__(self, 5, 1, -1, 1, 1)

    def __init__(self, path, last_days, last_week, last_month, last_quarter, last_year):
        self.path = path
        self.last_days = Periods(1, last_days)
        self.last_week = Periods(7, last_week)
        self.last_month = Periods(28, last_month)
        self.last_quarter = Periods(91, last_quarter)
        self.last_year = Periods(365, last_year)

        #stockage des listes de fichier par dossier parent <parent_path: list()>
        self._all_files = dict()
        #stockage des fichiers à conserver
        self._all_retention_file = list()


    def _make_file_list(self, parent_path=""):
        """Parcour récursif du dossier entré afin de remplir self._all_files
        @param dossier à parcourir"""

        if parent_path == "":
            parent_path = self.path

        #liste les fichiers présents dans le dossier
        for fichier in os.listdir(parent_path):
            #on remet le dossier parent devant
            fichier = parent_path + "/" + fichier
            if os.path.exists(fichier) and os.path.islink(fichier) == False:
                #si c'est un dossier
                if os.path.isdir(fichier):
                    #on ré-itère
                    self._make_file_list(fichier)
                else:
                    ext = os.path.splitext(fichier)
                    if len(ext) == 2:
                        if ext[1] == ".xz":
                            #c'est des fichiers .xz
                            if parent_path not in self._all_files:
                                self._all_files[parent_path] = list()

                            self._all_files[parent_path].append(fichier)
            else:
                print("*** : OOOPS {} n'est pas un fichier ???".format(fichier))
                print("*** {}, exists = {}, islink = {}".format(fichier, os.path.exists(fichier), os.path.islink(fichier)))

    def _get_matching_files(self):
        """Pour toutes les périodes de rétentions créées et les dossiers parents détectés
        récupère les fichiers renvoyés par Periods et les ajoute à self._all_retention_file"""

        for path in self._all_files.keys():
            self._all_retention_file.extend(self.last_year.get_matching_files_list(self._all_files[path]))
            self._all_retention_file.extend(self.last_quarter.get_matching_files_list(self._all_files[path]))
            self._all_retention_file.extend(self.last_month.get_matching_files_list(self._all_files[path]))
            self._all_retention_file.extend(self.last_week.get_matching_files_list(self._all_files[path]))
            self._all_retention_file.extend(self.last_days.get_matching_files_list(self._all_files[path]))

    def _remove_unwanted_files(self, parent_path=""):
        """supprime les fichiers de self._all_files absents de self._all_retention_files

        Parcour récursif du dossier
        @param dossier à parcourir"""

        if parent_path == "":
            parent_path = self.path

        #liste les fichiers présents dans le dossier
        for fichier in os.listdir(parent_path):
            #on remet le dossier parent devant
            fichier = parent_path + "/" + fichier
            if os.path.exists(fichier) and os.path.islink(fichier) == False:
                #si c'est un dossier
                if os.path.isdir(fichier):
                    #on ré-itère
                    self._remove_unwanted_files(fichier)
                else:
                    ext = os.path.splitext(fichier)
                    if len(ext) == 2:
                        if ext[1] == ".xz": #c'est des fichiers .xz
                            if fichier not in self._all_retention_file:#regarde si il a le droit de le supprimer
                                print("J'ai le droit de supprimer le fichier {} :p".format(fichier))
                                os.remove(fichier)
            else:
                print("*** : OOOPS {} n'est pas un fichier ???".format(fichier))
                print("*** {}, exists = {}, islink = {}".format(fichier, os.path.exists(fichier), os.path.islink(fichier)))

    def run(self):
        print("Démarrage de la rétention sur", self.path)
        self._make_file_list()
        self._get_matching_files()
        self._remove_unwanted_files()


def load_retention(retentions_param):
    """Charge une liste de classe Retention avec les paramètres entrés"""
    retentions = list()

    for retention_param in retentions_param:
        retentions.append(Retention(*retention_param))

    return retentions

#charge le fichier de configuration
sys.path.append("/etc/save")
import retention_conf

#charge les opérations de rétention à faire
retentions = load_retention(retention_conf.retentions)

for retention in retentions:
    retention.run()


