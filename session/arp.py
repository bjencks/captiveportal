#!/usr/bin/python3
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
"""
CREATE TABLE sessions (
  id INTEGER PRIMARY KEY,
  ip ipv4addr,
  mac macaddr
);
CREATE TABLE queue (
  id INTEGER PRIMARY KEY,
  action TEXT,
  mac macaddr,
  ip ipv4addr,
  time timestamp
);
"""

import session
from mac import MAC
import ipaddr
import datetime
import sqlite3
import common
import time
import subprocess
import arpnd

LOGGER = session.setup_logging('arp-watcher')

KEY =  b"z\xee\xd3\x0e\x83z\xee\x8a]\t\xb45\x8c\xb9]MP^gwo\x83\x03\xccdi\xb7\x9b:?e*\xc71\xd2\xb1\x8c\x9eo\xb5\xc0I+<{\xdb\xc2\x08l\x87\x05\xc8\xbf\xc8j\x84'C\x1f\xe7\xef\xef\xfb\xc8"

VALID_IFACE = 'eth0.10'

def enqueue_session(con, action, mac, ip):
    con.execute('INSERT INTO queue (action, mac, ip, time)'
                ' VALUES (?,?,?,?)', (action, mac, ip, datetime.datetime.utcnow()))
def start_session(con, mac, ip):
    con.execute('INSERT INTO sessions (mac, ip) VALUES (?,?)', (mac, ip))
    enqueue_session(con, 'start', mac, ip)
    LOGGER.info('Session started: {0!r} {1!r}'.format(mac, ip))
def end_session(con, sessid, mac, ip):
    con.execute('DELETE FROM sessions WHERE id = ?', (sessid,))
    enqueue_session(con, 'end', mac, ip)
    LOGGER.info('Session ended: {0!r} {1!r}'.format(mac, ip))


def session_exists(con, sess):
    if con.execute('SELECT id FROM sessions WHERE mac = ? AND ip = ?', sess).fetchone():
        return True
    return False

def get_open_sessions(con):
    for row in con.execute('SELECT id, mac, ip FROM sessions'):
        yield row

def pop_session(con):
    row = con.execute('SELECT id, action, mac, ip, time FROM queue LIMIT 1').fetchone()
    if row:
        sessid, action, mac, ip, time = row
        con.execute('DELETE FROM queue WHERE id = ?', (sessid,))
        return {'action': action, 'mac': mac, 'ipv4': ip, 'time': time}
    return None

def main(con):
    with con:
        current_sessions = arpnd.get_current_sessions(4, VALID_IFACE)
        for sessid, mac, ipv4 in get_open_sessions(con):
            if (mac, ipv4) not in current_sessions:
                end_session(con, sessid, mac, ipv4)
        for mac, ipv4 in current_sessions:
            if not session_exists(con, (mac, ipv4)):
                start_session(con, mac, ipv4)
    while True:
        with con:
            sess = pop_session(con)
            if not sess:
                break
            sess.update({'source': 'arp', 'key': KEY})
            session.submit_session(**sess)

sqlite3.register_adapter(ipaddr.IPv4Address, lambda x: x.packed)
sqlite3.register_converter('ipv4addr', ipaddr.IPv4Address)
sqlite3.register_adapter(MAC, lambda m: m.bytes)
sqlite3.register_converter('macaddr', MAC)

if __name__ == '__main__':
    con = sqlite3.connect('arp.db', detect_types=sqlite3.PARSE_DECLTYPES)

    while True:
        try:
            main(con)
        except:
            LOGGER.exception('Exception occured')
        time.sleep(30)
