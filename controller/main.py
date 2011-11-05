#!/usr/bin/env python

import logging
import cherrypy
import sessions
from mac import MAC
import ipaddr
import datetime
import xml.sax.saxutils
import urllib.parse
import config
import common

def logger():
    return logging.getLogger('main')

class AppMain:
    @cherrypy.expose
    def index(self):
        yield """<html>
<head><title>Session list</title>
<style type="text/css">
table, th, td {
    border: 1px solid black;
}
</style>
</head>
<body>
  <table>
    <tr>
      <th>User</th><th>MAC</th><th>Start</th><th>End</th><th>Source</th><th>IPv4</th><th>IPv6</th><th>Start</th><th>End</th>
    </tr>
"""
        for row in sessions.all_sessions():
            row = list(row)
            if row[0]:
                row[0] = xml.sax.saxutils.escape(row[0])
            else:
                row[0] = ''
            yield "<tr><td>{0}</td><td>{1!s}</td><td>{2!s}</td><td>{3!s}</td><td>{4}</td><td>{5!s}</td><td>{6!s}</td><td>{7!s}</td><td>{8!s}</td></tr>".format(*row)
        yield """
  </table>
</body>
</html>"""

    @cherrypy.expose
    def session(self, action=None, source=None, mac=None, ipv4=None, ipv6=None, time=None):
        if cherrypy.request.method != 'POST':
            return "Invalid request method"
        if source not in ('arp', 'nd', 'radius', 'dhcp'):
            return "Invalid source"
        self.authenticate_session_request()
        mac = MAC(mac)
        if ipv4:
            ipv4 = ipaddr.IPv4Address(ipv4)
        if ipv6:
            ipv6 = ipaddr.IPv6Address(ipv6)
        time = datetime.datetime.strptime(time, "%Y-%m-%dT%H:%M:%S")
        if action == 'start':
            sessions.session_started(source, mac, time, ipv4, ipv6)
        elif action == 'end':
            sessions.session_ended(source, mac, time, ipv4, ipv6)
        else:
            return "Invalid action"
        return "Success"

    @cherrypy.expose
    def splash(self, mac=None, origurl=None):
        macval = MAC(mac) # Ensures mac is a safe string
        yield """<html>
<head><title>Wifi Login</title></head>
<body>
  <form action="/login" method="POST">
    <input type="hidden" name="mac" value="{mac}"/>
""".format(mac=mac)
        if origurl:
            yield '    <input type="hidden" name="origurl" value={0}/>'.format(xml.sax.saxutils.quoteattr(origurl))
        yield """
    <label>Username: <input type="text" name="user"/></label>
    <input type="submit" value="Log in"/>
  </form>
</body></html>
"""

    @cherrypy.expose
    def login(self, user=None, mac=None, origurl=None):
        if cherrypy.request.method != 'POST':
            return self.splash(mac, origurl)
        mac = MAC(mac)
        sessions.user_logged_in(user, mac)
        params = {'user': user}
        if origurl:
            params['origurl'] = origurl
        url = '{0}/welcome?{1}'.format(cherrypy.request.base,
                urllib.parse.urlencode(params))
        raise cherrypy.HTTPRedirect(url)

    @cherrypy.expose
    def welcome(self, user=None, origurl=None):
        yield """<html><head><title>Welcome to wifi</title></head>
<body>
<p>Thanks for logging in, {0}</p>
""".format(xml.sax.saxutils.escape(user))
        if origurl:
            yield "<p>Continue on to <a href={0}>{1}</a></p>".format(
                        xml.sax.saxutils.quoteattr(origurl),
                        xml.sax.saxutils.escape(origurl))
        yield "</body></html>"

    def authenticate_session_request(self):
        """Ensures that the current request is properly signed. Raises an
        exception if the signature is invalid. Performs no validation that the
        parameters are sensible.

        """
        args = dict(cherrypy.request.body.params)
        args['key'] = config.SESSION_KEYS[args['source']]
        if cherrypy.request.headers['Authorization'] != common.gen_authorization_header(**args):
            raise Exception('Invalid HMAC signature')

def setup_logging():
    loghandler = logging.StreamHandler()
    loghandler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(message)s'))
    rootlogger = logging.getLogger()
    rootlogger.addHandler(loghandler)
    rootlogger.setLevel(logging.DEBUG)
setup_logging()
#cherrypy.config.update({'server.socket_host': '::',
#                        'log.access_file': 'access.log',
#                        'log.error_file': 'error.log',
#                        'environment': 'production'})
cherrypy.config.update({'log.screen': False})
cherrypy.tree.mount(AppMain(), '/')
cherrypy.engine.start()
cherrypy.engine.block()

