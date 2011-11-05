#!/usr/bin/python3.1

import session
import mac
import ipaddr
import datetime

session.setup_logging()

KEY =  b'\xbf\x11\xbf\x94\x06D87\xe2\x05\x1f_[/\x17sY\xe6\x16\xa5\x96B\x91{\x87\x06$2\xa9\x14sx\xa7\xe2\x97\xaePiO\xc4p\xf5G\xfb\x98\x9a\xdf\x12\xca\x8c\xe7!\xbd\xf4\xe5uo?_|\x99\x9f\xc9T'

def do_session(action, mac, ip):
    session.enqueue_session({'action': action, 'source': 'nd', 'mac': mac, 'ipv6': ip, 'time': datetime.datetime.utcnow()})
def start_session(mac, ip):
    do_session('start', mac, ip)
def end_session(mac, ip):
    do_session('end', mac, ip)


import sys

do_session(sys.argv[1], mac.MAC(sys.argv[2]), ipaddr.IPv6Address(sys.argv[3]))

session.submit_sessions(KEY)
