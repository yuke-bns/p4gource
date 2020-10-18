#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Perforceのログをgource形式へ変換して出力する。
#
#
"""
MIT License

Copyright (c) 2020 HIROMATSU Yusuke

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

__author__  = "HIROMATSU Yusuke"
__email__ = "yuke.x68@gmail.com"

import argparse
import logging
import fnmatch
import time
import sys
from P4 import P4
from P4 import P4Exception


"""
    PerforceログをGourceで取り込める形式に変換するクラス。
"""
class P4Gource:
    def __init__(self, options):
        self.p4Session = P4()

        if options.p4user:
            self.p4Session.user = options.p4user

        if options.p4password:
            self.p4Session.password = options.p4password

        if options.p4server:
            self.p4Session.port = options.p4server

        self.p4Session.connect()
        self.p4Session.run_login()

        self.fileList = list()


    """
        p4ログを取り込む
    """
    def read_p4_logs(self, revfrom, revto, includes, excludes):
        if not revfrom:
            revfrom = 1

        if not includes:
            includes = tuple()

        if not excludes:
            excludes = tuple()

        print(includes)

        #最新リビジョンまで読むようにする。
        if revto <= 0:
            info = self.p4Session.run_changes('-s', 'submitted', '-m', 1)[0]
            revto = int(info['change'])

        logging.info("Read logs from %d to %d.", revfrom, revto)

        for k in range(revfrom, revto + 1):
            try:
                result = self.p4Session.run_describe('-s', k)

                if not result or len(result) <= 0:
                    continue

            except P4Exception as ex:
                logging.warning("rev %d failed: %s", k, ex)
                continue

            desc = result[0]
            if desc['status'] != 'submitted':
                continue

            logging.info("Reading Rev.%d...", k)

            descTime = desc['time']
            descUser = desc['user']

            for k in zip(desc['depotFile'], desc['action']):
                filePath = k[0].strip().strip('/')

                if len(includes) > 0:
                    if not any(fnmatch.fnmatch(filePath, path) for path in includes):
                        logging.debug("skipping %s", filePath)
                        continue

                if any(fnmatch.fnmatch(filePath, path) for path in excludes):
                    continue

                action = 'M'

                if k[1] == 'add' or k[1] == 'move/add':
                    action = 'A'

                elif k[1] == 'delete' or k[1] == 'move/delete':
                    action = 'D'

                elif k[1] == 'edit':
                    action = 'M'

                else:
                    logging.warning("unknown action %s: %s", k[1], filePath)

                self.fileList.append([
                    descTime, descUser, action, filePath
                ])

        return self.fileList

    """
        ログを出力する。
    """
    def write_log(self, fileDest):
        fileDest.writelines('|'.join(info) + "\n" for info in self.fileList)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('-v', '--verbose', default='info', choices=('info', 'debug'),
                        help='ログ出力レベル')
    parser.add_argument('-q', '--p4user', help='Perforceユーザ名')
    parser.add_argument('-r', '--p4password', help='Perforceパスワード')
    parser.add_argument('-s', '--p4server', help='アクセス先Perforceサーバ')

    parser.add_argument('-o', '--output', help='出力先ログファイル')
    parser.add_argument('-p', '--path', action='append', help='取り込む対象ファイル、フォルダパス。複数指定可。')
    parser.add_argument('-x', '--exclude', action='append', help='無視するファイル、フォルダパス。複数指定可。--includeより優先される。')

    #parser.add_argument('-i', '--initialize', action='store_true', help='取得開始リビジョン番号')
    parser.add_argument('-f', '--revfrom', type=int, help='取得開始リビジョン番号', default=1)
    parser.add_argument('-t', '--revto', type=int, help='取得終了リビジョン番号', default=-1)

    options = parser.parse_args()
    logFormat = '%(asctime)s [%(levelname)s] : %(message)s'

    if options.verbose == 'debug':
        logging.basicConfig(level=logging.DEBUG, format=logFormat)
    else:
        logging.basicConfig(level=logging.INFO, format=logFormat)

    task = P4Gource(options)

    task.read_p4_logs(options.revfrom, options.revto, options.path, options.exclude)

    if options.output:
        with open(options.output, "w") as f:
            task.write_log(f)
    else:
        task.write_log(sys.stdout)

    exit(0)
