#!/usr/bin/python3

import sys
import arpnd
import asyncserver
import logging
import logging.handlers
import urllib.parse
import xml.sax.saxutils
import datetime

PORT = 8080

REDIR_URL = b'http://localhost:8090/splash'

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

if __name__ == "__main__":
    asyncserver.main(PORT, RedirectorServer)
