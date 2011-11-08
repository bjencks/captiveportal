#!/usr/bin/python3

import sys
import os
import arpnd
import asyncserver
import logging
import logging.handlers
import urllib.parse
import xml.sax.saxutils
import datetime
import socket
import pwd

PORT = 8080

REDIR_URL = b'http://vps.bjencks.net:8080/splash'

# Should really be socket.IP_TRANSPARENT, but it's not defined there.
IP_TRANSPARENT = 19

# Drop privileges to this user and its group
RUNAS = 'nobody'

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

def url_from_request(request):
    lines = request.splitlines()
    line1 = lines[0]
    headerlines = lines[1:]
    (method, path, vers) = line1.split(b' ', 2)
    host = None
    for line in headerlines:
        if line.lower().startswith(b'host: '):
            host = line[6:].strip()
            break
    if not host:
        return None
    return b'http://' + host + path

class RedirectorServer(asyncserver.BufferedSocket):
    def request_complete(self):
        return (self.readbuf.find(b'\n\r\n') >= 0
                or self.readbuf.find(b'\n\n') >= 0)
    def generate_response(self):
        oldurl = url_from_request(self.readbuf)
        macobj = arpnd.get_mac_for_addr(self.get_address())
        if not macobj:
            raise Exception("MAC for {0} not found".format(self.addr[0]))
        mac = macobj.rawstr().encode('ascii')
        qs = b'mac=' + mac
        if oldurl:
            qs += (b'&origurl=' + 
                   urllib.parse.quote_plus(oldurl).encode('ascii'))
        url = REDIR_URL + b'?' + qs
        content = (b'''\
<html><head>
<title>Redirect</title>
</head><body>
<h1>Redirect</h1>
<p>You are being redirected to <a href='''
+ xml.sax.saxutils.quoteattr(url.decode('ascii')).encode('ascii')
+ b'''>here</a>.</p>
</body></html>
''')

        self.writebuf += b'HTTP/1.1 302 Found\r\n'
        self.writebuf += b'Date: ' + datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT').encode('ascii') + b'\r\n'
        self.writebuf += b'Location: ' + url + b'\r\n' 
        self.writebuf += b'Content-Length: ' + str(len(content)).encode('ascii') + b'\r\n'
        self.writebuf += b'Content-Type: text/html; charset=us-ascii\r\n'
        self.writebuf += b'\r\n'
        self.writebuf += content

def drop_privs():
    pwdent = pwd.getpwnam(RUNAS)
    os.setgid(pwdent.pw_gid)
    os.setuid(pwdent.pw_uid)

if __name__ == "__main__":
    addrinfos = socket.getaddrinfo(None, PORT, 0, socket.SOCK_STREAM,
                                   socket.SOL_TCP, socket.AI_PASSIVE)
    listeners = []
    for (family, socktype, proto, _, sockaddr) in addrinfos:
        sock = socket.socket(family, socktype, proto)
        if family == socket.AF_INET6:
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_IP, IP_TRANSPARENT, 1)
        sock.bind(sockaddr)
        sock.listen(255)
        listeners.append(sock)
    drop_privs()
    asyncserver.main(listeners, RedirectorServer)
