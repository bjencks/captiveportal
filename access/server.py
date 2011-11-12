#!/usr/bin/python3

import sys
import os
import asyncserver
import logging
import logging.handlers
import urllib.parse
import datetime
import socket
import netstring
from mac import MAC
import hashlib
import hmac
import base64

PORT = 7000

TIMEWINDOW = datetime.timedelta(minutes=1) # Plus or minus one minute

ACCESSKEY = b'\xd7\xb4\xaa\x1fZ^\x8c\x93\x80\xa6\xccC}\x86T\xf1^\xeb\x05\xcb\xce\xe6\xd4\xcf\x04\xa9()E\xcer\xf5\x9c\x1eq\xf0P\x03\xe3\x8bg\x9e\x08ZY\x83\xfa\x17\x8fU\x82\x19qMV\x9bd\xa9*\xc5\xbf\xa6\xc9\xee'

def setup_logging(name):
    loghandler = logging.handlers.SysLogHandler('/dev/log',
                    logging.handlers.SysLogHandler.LOG_DAEMON)
    loghandler.setFormatter(logging.Formatter("{0}: (%(name)s) %(message)s".format(name)))
    stderrhandler = logging.StreamHandler()
    stderrhandler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(message)s'))
    rootlogger = logging.getLogger()
    #rootlogger.addHandler(loghandler)
    rootlogger.addHandler(stderrhandler)
    rootlogger.setLevel(logging.DEBUG)
    def exc_handler(typ, val, tb):
        rootlogger.critical("Exception occurred", exc_info=(typ, val, tb))

    sys.excepthook = exc_handler
    return rootlogger

LOGGER = setup_logging('redirector')

class AccessServer(asyncserver.BufferedSocket):
    def request_complete(self):
        return netstring.is_netstring(self.readbuf)
    def generate_response(self):
        (request, _) = netstring.consume_netstring(self.readbuf)
        (sig, request) = netstring.consume_netstring(request)
        sig = base64.standard_b64decode(sig)
        mysig = hmac.new(ACCESSKEY, request, hashlib.sha256).digest()
        if sig != mysig:
            self.writebuf = b'ERROR Bad signature'
            return
        (action, request) = netstring.consume_netstring(request)
        (mac, request) = netstring.consume_netstring(request)
        (time, request) = netstring.consume_netstring(request)
        if len(request) > 0:
            raise Exception('Invalid request: too long: ' + repr(self.readbuf))
        mac = MAC(mac.decode('ascii'))
        time = datetime.datetime.strptime(time.decode('ascii'),
                                          '%Y-%m-%dT%H:%M:%S')
        now = datetime.datetime.utcnow()
        if time < (now - TIMEWINDOW) or time > (now + TIMEWINDOW):
            self.writebuf = b'ERROR Time out of sync'
            return
        if action not in (b'grant', b'revoke'):
            self.writebuf = b'ERROR Invalid action'
            return
        LOGGER.info('Valid request to {0!r} {1!s}'.format(action, mac))
        if action == b'grant':
            print('grant', str(mac))
        elif action == b'revoke':
            print('revoke', str(mac))
        sys.stdout.flush()
        resp = sys.stdin.readline().strip()
        if resp == 'OK':
            self.writebuf = netstring.encode_netstring(b'OK')
        else:
            self.writebuf = netstring.encode_netstring(b'ERROR ' + resp.encode('ascii'))

if __name__ == "__main__":
    addrinfos = socket.getaddrinfo(None, PORT, 0, socket.SOCK_STREAM,
                                   socket.SOL_TCP, socket.AI_PASSIVE)
    listeners = []
    for (family, socktype, proto, _, sockaddr) in addrinfos:
        sock = socket.socket(family, socktype, proto)
        if family == socket.AF_INET6:
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(sockaddr)
        sock.listen(255)
        listeners.append(sock)
    asyncserver.main(listeners, AccessServer)

