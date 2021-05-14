# -*- coding: utf8 -*-
# ------------------------------------------------------------------------------
# Name:        compression
# Purpose:     Compress / Decompress
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
import time
import logging
import subprocess
import os
from enum import Enum
from string import Template
from pathlib import Path

from snr.units import Units
from snr.yamlhelper import YAMLHelper

logger = logging.getLogger(__name__)


class CMode(Enum):
    COMPRESS = 1
    DECOMPRESS = 2
    DUMP = 3
    RESTORE = 4


class Compression:
    """
    Compression helper factory. Configured through yaml config file via compression_helpers key
    """

    C_YAML = """
compression_helpers:
  #compressed_extention: tar.xz
  compressed_from_pipe_ext: xz
  compressed_extention: tar.lzo
  #compressed_from_pipe_ext: lzo
  compress_env:
    XZ_OPT: "-0 --threads=5"
    LZOP: '--fast'
  compress_command: [
    '/bin/tar',
    '--create',
    #'--xz',
    '--lzop',
    '--exclude=*.socket',
    '--exclude=socket',
    '--file',
    '$destination',
    '$file'
  ]
  compress_info_command: [
    '/usr/bin/lzop',
    '-l',
    '$file'
  ]
  compress_info_command_output: {
    'data_line': -1,
    'compressed_size_index': 1,
    'uncompressed_size_index': 2,
    'ratio_index': 3
  }
  compress_from_pipe: [
    '/usr/bin/xz'
    #'/usr/bin/lzop'
  ]
  compress_from_pipe_info: [
    '/usr/bin/xz',
    '--robot',
    '--list',
    '$file'
  ]
  compress_from_pipe_info_output: {
    'data_line': -1,
    'compressed_size_index': 3,
    'uncompressed_size_index': 4,
    'ratio_index': 5
  }
  decompress_command: [
    '/bin/tar',
    'xaf',
    '$file'
  ]
  decompress_to_pipe: [
    '/usr/bin/xzcat',
    #'/usr/bin/lzop',
    #'-dc',
    '$file'
  ]
"""

    cache = dict()
    C_HELPERS = 'compression_helpers'
    C_HELPER_KEYS = {
        'compressed_extention', 'compressed_from_pipe_ext', 'compress_env',
        'compress_command', 'decompress_command',
        'compress_from_pipe', 'decompress_to_pipe',
        'compress_info_command', 'compress_info_command_output',
        'compress_from_pipe_info', 'compress_from_pipe_info_output'
    }

    def __init__(
            self,
            compressed_extention=None,
            compressed_from_pipe_ext=None,
            compress_env=None,
            compress_command=None,
            decompress_command=None,
            compress_from_pipe=None,
            decompress_to_pipe=None,
            compress_info_command=None,
            compress_info_command_output=None,
            compress_from_pipe_info=None,
            compress_from_pipe_info_output=None
    ):
        """
        Should not be used directly
        """
        self._compressed_extention = compressed_extention
        self._compressed_from_pipe_ext = compressed_from_pipe_ext
        self._compress_env = compress_env
        self._compress_command = compress_command
        self._decompress_command = decompress_command
        self._compress_from_pipe = compress_from_pipe
        self._decompress_to_pipe = decompress_to_pipe
        self._compress_info_command = compress_info_command
        self._compress_info_command_output = compress_info_command_output
        self._compress_from_pipe_info = compress_from_pipe_info
        self._compress_from_pipe_info_output = compress_from_pipe_info_output

    @property
    def extensions(self):
        """
        :return: Set of compressed file extensions
        :rtype: set
        """
        return {self._compressed_extention, self._compressed_from_pipe_ext}

    def get_file_with_compressed_extension(self, file):
        return "{}.{}".format(file, self._compressed_extention)

    def get_file_with_compressed_from_pipe_ext(self, file):
        return "{}.{}".format(file, self._compressed_from_pipe_ext)

    @staticmethod
    def get_instance(conf):
        """
        Compression class Factory. Instances are cached by 'conf' parameter.
        :param conf: path to Yaml configuration
        :return: instance of Compression
        :rtype: Compression
        """
        # Is conf unknown in cache ?
        if conf not in Compression.cache.keys():
            try:
                data = YAMLHelper.load(conf)
                # Validate configuration keys
                YAMLHelper.analyse_keys(Compression.C_HELPERS, data[Compression.C_HELPERS], Compression.C_HELPER_KEYS)
                # Instanciate and cache
                Compression.cache[conf] = Compression(**data[Compression.C_HELPERS])
            except TypeError as e:
                logger.error("Compression configuration error : {}".format(e))
            except IOError:
                logger.error("{} does not exist".format(conf))
        # return cached instance
        return Compression.cache[conf]

    def is_compressed(self, file):
        """
        Check file extension and return True if endswith self._compressed_extention or self._compressed_from_pipe_ext
        :param file: file path to check
        :type file: str
        :rtype: bool
        """
        if file.endswith(self._compressed_extention) or file.endswith(self._compressed_from_pipe_ext):
            return True
        return False

    @staticmethod
    def _create_folder(destination, is_dir=False):
        """
        Act like mkdir -p. Remove file part from destination string unless is_dir set to true.
        :param destination: folder(s) to create
        :type destination: str
        :param is_dir: Optional, default to False
        :type is_dir: bool
        :raise: PermissionError
        """
        if is_dir:
            save_dir = destination
        else:
            save_dir = os.path.split(destination)[0]
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

    def compress_from_pipe(self, pipe, destination):
        """
        Compress stream from pipe to destination.
        Compression extension will be added to destination file.
        :param pipe: will be used as stdin for the compression process.
        :type pipe: subprocess.PIPE
        :param destination: destination file without extention
        :type destination: str
        :return: compressed file name, None on error
        :rtype: Union[str|None]
        """
        if pipe is None:
            logger.error("Pipe is None, aborting compress_from_pipe()")
            return None

        self._create_folder(destination)
        destination = "{}.{}".format(destination, self._compressed_from_pipe_ext)

        for env in self._compress_env.keys():
            os.environ[env] = self._compress_env[env]

        logger.info("running {}".format(self._compress_from_pipe))
        with open(destination, 'wb') as f:
            p = subprocess.Popen(self._compress_from_pipe, stdin=pipe, stdout=f)

        # start process and wait until it finishes
        p.communicate()

        if p.returncode == 0:
            return destination

        logger.error(p)
        return None

    def compress(self, source, destination):
        """
        Compress source directory to destination file. Compress extension will be appended to destination file.
        Abort and delete partial file on any error.
        Strips all directories in source.
        :param source: source directory to compress
        :type source: str
        :param destination: destination file without extension
        :type destination: str
        :return: destination or None if error
        :rtype: Union[str|None]
        """
        if not os.path.exists(source):
            logger.error("{} does not exist. Aborting compress()".format(source))
            return None

        destination = "{}.{}".format(destination, self._compressed_extention)

        for env in self._compress_env.keys():
            os.environ[env] = self._compress_env[env]

        cmd = list()
        for arg in self._compress_command:
            cmd.append(Template(arg).safe_substitute(
                file='.',
                destination=destination
            ))
        p = None
        try:
            start = time.time()
            Compression._create_folder(destination)
            logger.info("Compress {} to {}".format(source, destination))
            logger.info("running {}".format(cmd))
            p = subprocess.Popen(cmd, stderr=subprocess.PIPE, cwd=source)
            err_count = 0
            with p.stderr as err:
                for msg in err:
                    # avoid stopping tar when issuing 'Removing leading `/' from member names'
                    if err_count > 0:
                        msg = msg.decode().replace('\n', '')
                        logger.error("Compression {} to {} : {}".format(source, destination, msg))
                        raise ChildProcessError(msg)
                    err_count += 1

            p.wait()
            if p.returncode == 0:
                seconds = time.time() - start
                original_size = self.get_folder_size(source)
                logger.info(Compression.get_statistics(original_size, destination, seconds, CMode.COMPRESS))
                return destination
            logger.error(p)
            return None
        except KeyboardInterrupt:
            if p:
                logger.warning("Caught keyboard interrupt. Terminating compression of {}".format(source))
                p.terminate()
                logger.warning("Deleting partial file {}".format(destination))
                Compression.delete(destination)
                return None
        except ChildProcessError:
            p.terminate()
            logger.warning("Deleting partial file {}".format(destination))
            Compression.delete(destination)
            return None
        except PermissionError as e:
            logger.error("Cannot create directory {} : {}".format(destination, e))
            return None

    @staticmethod
    def delete(file):
        """
        Delete file if exists
        :param file: file to delete
        :type file: str
        """
        if os.path.exists(file):
            logger.info("Deleting {}".format(file))
            os.remove(file)

    def decompress_to_pipe(self, file):
        """
        Decompress a file and return stream (stdout)
        :param file: file to decompress
        :type file: str
        :return: decompressed stream
        :rtype: subprocess.PIPE
        """
        if not os.path.exists(file):
            logger.error("{} does not exists. Aborting decompress_to_pipe().".format(file))
            return None
        cmd = list()
        for arg in self._decompress_to_pipe:
            cmd.append(Template(arg).safe_substitute(file=file))
        logger.info("running {}".format(cmd))
        return subprocess.Popen(cmd, stdout=subprocess.PIPE)

    def decompress(self, file, destination):
        """
        Decompress file in destination folder
        :param file: file to decompress
        :type file: str
        :param destination: destination folder
        :type destination: str
        :return: destination folder, None on error
        :rtype: Union[str|None]
        """
        start = time.time()
        if not os.path.exists(file):
            logger.error("Source {} does not exists. Aborting decompress().".format(file))
            return None

        if not os.path.exists(destination):
            logger.warning("Creating dir {}".format(destination))
            try:
                Compression._create_folder(destination, is_dir=True)
            except PermissionError as e:
                logger.error("Cannot create directory {} : {}".format(destination, e))
                return None

        cmd = list()
        for arg in self._decompress_command:
            cmd.append(Template(arg).safe_substitute(file=file))
        logger.info("running {}".format(cmd))
        try:
            p = subprocess.run(cmd, cwd=destination)
            if p.returncode == 0:
                seconds = time.time() - start
                original_size = self.get_folder_size(destination)
                logger.info(Compression.get_statistics(original_size, file, seconds, CMode.DECOMPRESS))
                return destination
            logger.error(p)
            return None
        except KeyboardInterrupt:
            logger.warning("Caught KeyboardInterrupt !")
            return None
        except ChildProcessError as e:
            logger.warning("{}".format(e))
            return None
        except PermissionError as e:
            logger.error("Cannot read {} : {}".format(destination, e))
            return None
        except FileNotFoundError as e:
            logger.error("Cannot decompress in {} : {}".format(destination, e))
            return None

    @staticmethod
    def get_folder_size(folder):
        """
        Returns folder size
        :param folder: folder path
        :type folder: str
        :return: size in bytes
        :rtype: int
        """
        root_directory = Path('.')
        return sum(f.stat().st_size for f in root_directory.glob('**/*') if f.is_file())

    def get_statistics(self, file, seconds, mode):
        """
        :param file: compressed file path
        :type file: str
        :param seconds: time in second to perform COMPRESSION or DECOMPRESSION
        :type seconds: float
        :param mode: Display stats for COMPRESSION or DECOMPRESSION
        :type mode: CMode
        :return: statistics
        :rtype: str
        """
        if file.endswith(self._compressed_extention):
            cmd = list()
            for arg in self._compress_info_command:
                cmd.append(Template(arg).safe_substitute(file=file))
            output = self._compress_info_command_output
        elif file.endswith(self._compressed_from_pipe_ext):
            cmd = list()
            for arg in self._compress_from_pipe_info:
                cmd.append(Template(arg).safe_substitute(file=file))
            output = self._compress_from_pipe_info_output
        else:
            return

        logger.info("running {}".format(cmd))
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        lines = list()
        with p.stdout as out:
            for line in out:
                lines.append(line.decode())
        data_line = lines[output['data_line']].split()

        original_size_bytes = int(data_line[output['uncompressed_size_index']])
        original_size = Units.convert_bytes(original_size_bytes)
        compressed_size_bytes = int(data_line[output['compressed_size_index']])
        compressed_size = Units.convert_bytes(compressed_size_bytes)
        ratio = data_line[output['ratio_index']]
        time_spent = Units.convert_seconds(seconds)
        bitrate = Units.get_bitrate(original_size_bytes, seconds)

        if mode == CMode.COMPRESS:
            stats = 'Compressed {file} of {compressed_size} in {time_spent}. ' \
                    'Compression bitrate: {bitrate}, original size: {original_size}, ratio: {ratio}.'
        elif mode == CMode.DUMP:
            stats = 'Dumped {file} of {compressed_size} in {time_spent}. ' \
                    'Dump bitrate: {bitrate}, original size: {original_size}, ratio: {ratio}.'
        elif mode == CMode.DECOMPRESS:
            stats = 'Decompressed {file} of {compressed_size} in {time_spent}. ' \
                    'Decompression bitrate: {bitrate}, original size: {original_size}, ratio: {ratio}.'
        elif mode == CMode.RESTORE:
            stats = 'Restored {file} of {compressed_size} in {time_spent}. ' \
                    'Restoration bitrate: {bitrate}, original size: {original_size}, ratio: {ratio}.'

        return stats.format(
            file=file,
            compressed_size=compressed_size,
            time_spent=time_spent,
            bitrate=bitrate,
            original_size=original_size,
            ratio=ratio
        )

    @staticmethod
    def get_statistics(original_size_bytes, compressed_file, seconds, mode):
        """
        Gives statistics about file compression/decompression.
        :param original_size_bytes: uncompressed size in bytes
        :type original_size_bytes: int
        :param compressed_file: compressed file path
        :type compressed_file: str
        :param seconds: time in second to perform COMPRESSION or DECOMPRESSION
        :type seconds: float
        :param mode: Display stats for COMPRESSION or DECOMPRESSION
        :type mode: CMode
        :return: statistics
        :rtype: str
        """
        logger.debug("get_statistics({}, {}, {}, {})".format(original_size_bytes, compressed_file, seconds, mode))
        original_size = Units.convert_bytes(original_size_bytes)
        compressed_size_bytes = os.stat(compressed_file).st_size
        compressed_size = Units.convert_bytes(compressed_size_bytes)
        ratio = compressed_size_bytes / original_size_bytes
        time_spent = Units.convert_seconds(seconds)
        bitrate = Units.get_bitrate(original_size_bytes, seconds)

        if mode == CMode.COMPRESS:
            stats = 'Compressed {file} of {compressed_size} in {time_spent}. ' \
                    'Compression bitrate: {bitrate}, original size: {original_size}, ratio: {ratio}.'
        elif mode == CMode.DUMP:
            stats = 'Dumped {file} of {compressed_size} in {time_spent}. ' \
                    'Dump bitrate: {bitrate}, original size: {original_size}, ratio: {ratio}.'
        elif mode == CMode.DECOMPRESS:
            stats = 'Decompressed {file} of {compressed_size} in {time_spent}. ' \
                    'Decompression bitrate: {bitrate}, original size: {original_size}, ratio: {ratio}.'
        elif mode == CMode.RESTORE:
            stats = 'Restored {file} of {compressed_size} in {time_spent}. ' \
                    'Restoration bitrate: {bitrate}, original size: {original_size}, ratio: {ratio}.'

        return stats.format(
            file=compressed_file,
            compressed_size=compressed_size,
            time_spent=time_spent,
            bitrate=bitrate,
            original_size=original_size,
            ratio=ratio
        )
