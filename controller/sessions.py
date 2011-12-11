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

import logging
import struct
import ipaddr
from dbconn import with_dbconn
import access_control
from mac import MAC
import common

class AlreadyLoggedInError(Exception):
    def __init__(self, user, mac, start):
        self.user = user
        self.mac = mac
        self.start = start
    def __str__(self):
        return 'User {0} already logged in at {1!r} since {2!s} UTC'.format(
                        self.user, self.mac, self.start)

def logger():
    return logging.getLogger('sessions')

# These three methods are the external module API:
@with_dbconn
def user_logged_in(con, user, mac):
    """Record a user as having logged in, and allow them access.

    Adds a row to user_sessions as well as finding all corresponding
    addr_sessions and updating them to point to this user session.
    """
    cur = con.execute('SELECT start FROM user_sessions'
                      ' WHERE user=? AND mac=? AND end IS NULL',
                      (user, mac.bytes))
    row = cur.fetchone()
    if row:
        raise AlreadyLoggedInError(user, mac, row[0])
    con.execute('INSERT INTO user_sessions (user, mac, start)'
                ' VALUES (?,?,datetime(\'now\'))',
                (user, mac.bytes))
    cur = con.execute('UPDATE addr_sessions'
                      ' SET user_session = last_insert_rowid()'
                      ' WHERE mac = ? AND end IS NULL', (mac.bytes,))
    logger().info(('Added user session for {0}/{1!r}, and matched'
                    ' {2:d} sessions').format(user, mac, cur.rowcount))
    access_control.authorize(mac)


@with_dbconn
def session_started(con, source, mac, time, ipv4=None, ipv6=None):
    """Record an address session.

    Possibly associates the session with any corresponding user session.
    """
    # # There's no one useful to return an error to, so we just close any
    # # previous open sessions, so we at least get a record that it got
    # # reopened.
    cur = con.execute('UPDATE addr_sessions SET end = ?'
                      ' WHERE source = ? AND mac = ? AND ipv4 IS ?'
                      ' AND ipv6 IS ? AND end IS NULL',
                      (time, source, mac.bytes, common.ipv4_to_bytes(ipv4),
                       common.ipv6_to_bytes(ipv6)))
    if cur.rowcount > 0:
        logger().warn(('Closed {0:d} existing {1} sessions for '
                       '{2!r} {3!r} {4!r}').format(cur.rowcount, source, mac,
                                                   ipv4, ipv6))
    cur = con.execute('SELECT id FROM user_sessions'
                      ' WHERE mac = ? AND end IS NULL', (mac.bytes,))
    row = cur.fetchone()
    if row:
        usersess = row[0]
        if cur.fetchone():
            logger().warn('More than one user session for {0!r}'.format(mac))
    else:
        usersess = None
    con.execute('INSERT INTO addr_sessions'
                ' (user_session, mac, source, ipv4, ipv6, start)'
                ' VALUES (?,?,?,?,?,?)',
                (usersess, mac.bytes, source, common.ipv4_to_bytes(ipv4),
                 common.ipv6_to_bytes(ipv6), time))
    logger().info(('Session from {2} started at {5!s}: {1!r} {3!r} {4!r}'
                    ' (matched with user session {0!s})'
                   ).format(usersess, mac, source, ipv4, ipv6, time))

@with_dbconn
def session_ended(con, source, mac, time, ipv4=None, ipv6=None):
    """Record a session ending.

    If enough of the user's address sessions have ended, terminate the user
    sessions and revoke their access.
    
    Current criteria: revoke if all arp and nd sessions for the mac have ended.
    """
    # Pseudocode:
    # SELECT id, user_session FROM addr_sessions WHERE source = ? AND mac = ?
    #   AND (ipv4/6 clause)
    #   (source, mac.bytes, ipv4/6)
    # UPDATE addr_sessions SET end = ? WHERE id = ?
    #   (time, id)
    # SELECT COUNT(*) FROM addr_sessions WHERE user_session = ?
    #   AND source IN ('arp', 'nd') AND end IS NULL
    #   (user_session)
    # if count == 0:
    #   end_user_session(con, user_session)
    pass
    cur = con.execute('SELECT id, user_session FROM addr_sessions'
                      ' WHERE source = ? AND mac = ?'
                      ' AND ipv4 IS ? AND ipv6 IS ? AND end IS NULL',
                      (source, mac.bytes, common.ipv4_to_bytes(ipv4),
                       common.ipv6_to_bytes(ipv6)))
    rows = cur.fetchall()
    addr_sessions = [row[0] for row in rows]
    user_sessions = set([row[1] for row in rows])
    if len(addr_sessions) > 1:
        logger().warn(('session_ended: More than one {0} session open for'
                       ' {1!r} {2!r} {3!r}. Closing all of them'
                      ).format(source, mac, ipv4, ipv6))
    if len(user_sessions) > 1:
        logger().error('session_ended: Multiple user sessions as well.')
    for addrsess in addr_sessions:
        con.execute('UPDATE addr_sessions SET end = ? WHERE id = ?',
                    (time, addrsess))
    for usersess in user_sessions:
        if usersess is not None:
            cur = con.execute('SELECT COUNT(*) FROM addr_sessions'
                              ' WHERE user_session = ?'
                              ' AND source IN (\'arp\', \'nd\') AND end IS NULL',
                              (usersess,))
            if cur.fetchone()[0] == 0:
                end_user_session(con, usersess)

@with_dbconn
def all_sessions(con):
    # KLUDGE: This function is entirely too view-oriented, and it's a bad view
    # at that. There should be a more abstract session model, but I needed
    # something quick-n-dirty to see what sessions there were.
    cur = con.execute('''SELECT user_sessions.user, addr_sessions.mac,
                            user_sessions.start, user_sessions.end,
                            addr_sessions.source, addr_sessions.ipv4,
                            addr_sessions.ipv6, addr_sessions.start,
                            addr_sessions.end
                         FROM addr_sessions LEFT OUTER JOIN user_sessions
                            ON addr_sessions.user_session = user_sessions.id
                         ORDER BY addr_sessions.start DESC''')
    # KLUDGE: This should be a generator, but since the generator gets passed
    # back up out of the with_dbconn decorator, the connection is closed before
    # the generator is evaluated.
    return [(row[0], MAC(row[1]), row[2], row[3], row[4], common.bytes_to_ipv4(row[5]),
             common.bytes_to_ipv6(row[6]), row[7], row[8]) for row in cur]
        

def end_user_session(con, sessid):
    """Close the user session, revoking access.

    Not for external use, only called from session_ended
    """
    # Pseudocode
    # UPDATE user_sessions SET end = datetime('now') WHERE id = ?
    #  (sessid)
    # SELECT mac FROM user_sessions WHERE id = ?
    #  (sessid)
    # access_control.revoke(mac)
    con.execute('UPDATE user_sessions SET end = datetime(\'now\')'
                ' WHERE id = ?', (sessid,))
    cur = con.execute('SELECT mac FROM user_sessions WHERE id = ?', (sessid,))
    mac = MAC(cur.fetchone()[0])
    try:
        access_control.revoke(mac)
    except:
        logger().exception('Failed to revoke mac {0!s}'.format(mac))

