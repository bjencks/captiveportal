# Copyright 2011 Ben Jencks
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sqlite3
import config


def dbconn():
    return sqlite3.connect(config.DBPATH, isolation_level='EXCLUSIVE',
                           detect_types=sqlite3.PARSE_DECLTYPES)

def with_dbconn(method):
    def meth(*args, **kwargs):
        con = dbconn()
        try:
            with con:
                if not isinstance(args, list):
                    args = list(args)
                args.insert(0, con)
                return method(*args, **kwargs)
        finally:
            con.close()
    return meth
