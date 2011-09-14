#!/usr/bin/env python

import logging
import cherrypy
import sessions
from mac import MAC
import ipaddr
import datetime

def logger():
    return logging.getLogger('main')

class AppMain:
    @cherrypy.expose
    def index(self):
        yield """<html>
<head><title>Session list</title></head>
<body>
  <table>
    <tr>
      <th>User</th><th>MAC</th><th>Start</th><th>End</th><th>Source</th><th>IPv4</th><th>IPv6</th><th>Start</th><th>End</th>
    </tr>
"""
        for row in sessions.all_sessions():
            yield "<tr><td>{0}</td><td>{1!s}</td><td>{2!s}</td><td>{3!s}</td><td>{4}</td><td>{5!s}</td><td>{6!s}</td><td>{7!s}</td><td>{8!s}</td></tr>".format(*row)
        yield """
  </table>
  <form action="/session" method="POST">
    <input type="hidden" name="source" value="arp">
    <b>ARP session:</b>
    <label>MAC: <input name="mac"></label>
    <label>IPv4: <input name="ipv4"></label>
    <button type="submit" name="action" value="start">Start</button>
    <button type="submit" name="action" value="end">End</button>
  </form>
  <form action="/session" method="POST">
    <input type="hidden" name="source" value="nd">
    <b>ND session:</b>
    <label>MAC: <input name="mac"></label>
    <label>IPv6: <input name="ipv6"></label>
    <button type="submit" name="action" value="start">Start</button>
    <button type="submit" name="action" value="end">End</button>
  </form>
  <form action="/session" method="POST">
    <input type="hidden" name="source" value="radius">
    <b>RADIUS session:</b>
    <label>MAC: <input name="mac"></label>
    <button type="submit" name="action" value="start">Start</button>
    <button type="submit" name="action" value="end">End</button>
  </form>
</body>
</html>"""

    @cherrypy.expose
    def session(self, action=None, source=None, mac=None, ipv4=None, ipv6=None, time=None):
        if cherrypy.request.method != 'POST':
            return "Invalid request method"
        if source not in ('arp', 'nd', 'radius', 'dhcp'):
            return "Invalid source"
        mac = MAC(mac)
        if ipv4:
            ipv4 = ipaddr.IPv4Address(ipv4)
        if ipv6:
            ipv6 = ipaddr.IPv6Address(ipv6)
        #time = datetime.datetime.strptime("%Y-%m-%dT%H:%M:%S", time)
        time = datetime.datetime.utcnow()
        if action == 'start':
            sessions.session_started(source, mac, time, ipv4, ipv6)
        elif action == 'end':
            sessions.session_ended(source, mac, time, ipv4, ipv6)
        else:
            return "Invalid action"
        return "Success"

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

