#!/usr/bin/python3

import subprocess
import os
import os.path
import sys
import pwd
import grp

CHILD_USER = 'nobody'
CHILD_GROUP = 'nogroup'

HEXCHRS = 'abcdefABCDEF0123456789'

TABLE = 'mangle'
CHAIN = 'allowed'

def read_request(pipe):
    req = pipe.readline().strip().decode('ascii')
    parts = req.split()
    if len(parts) != 2:
        raise Exception('Bad request: {0!r}'.format(req))
    command, mac = parts
    if command not in ('grant', 'revoke'):
        raise Exception('Invalid command {0!r} in request {1!r}'
                        .format(command, req))
    if not (len(mac) == 17 and mac.count(':') == 5
        and all([c == ':' for c in [mac[2], mac[5], mac[8], mac[11], mac[14]]])
        and all([c in HEXCHRS for c in [mac[0], mac[1], mac[3], mac[4], mac[6],
                                        mac[7], mac[9], mac[10], mac[12],
                                        mac[13], mac[15], mac[16]]])):
        raise Exception('Invalid MAC {0!r} in request {1!r}'.format(mac, req))
    return command, mac


def main(server_read, server_write):
    try:
        (command, mac) = read_request(server_read)
        print('Received request', command, mac)
        args = [None, '-t', TABLE, None, CHAIN, '-m', 'mac',
                '--mac-source', mac, '-j', 'ACCEPT']
        if command == 'grant':
            args[3] = '-A'
        elif command == 'revoke':
            args[3] = '-D'
        args[0] = '/sbin/iptables'
        subprocess.check_call(args)
        args[0] = '/sbin/ip6tables'
        subprocess.check_call(args)
        print('Request complete')
        server_write.write(b'OK\n')
        server_write.flush()
    except Exception as e:
        print('Error: ', repr(e))
        server_write.write(str(e).encode('ascii') + b'\n')
        server_write.flush()

def spawn_server():
    def pre_exec():
        user = pwd.getpwnam(CHILD_USER)
        group = grp.getgrnam(CHILD_GROUP)
        os.setgroups([])
        os.setgid(group.gr_gid)
        os.setuid(user.pw_uid)
    serverexec = os.path.join(os.path.dirname(sys.argv[0]), 'server.py')
    sub = subprocess.Popen(serverexec, stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE, preexec_fn=pre_exec)
    return (sub.stdout, sub.stdin)

if __name__ == "__main__":
    (server_read, server_write) = spawn_server();
    while True:
        main(server_read, server_write)
