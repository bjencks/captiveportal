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

PORT = 7000

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
        LOGGER.info('Request received: ' + str(self.readbuf))
        self.writebuf += netstring.encode_netstring(b'OK')

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

