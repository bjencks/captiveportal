import logging
import netstring
import config
import hmac
import base64
import hashlib
import socket
import datetime

def logger():
    return logging.getLogger('access_control')

def hmac_netstring(s):
    return netstring.encode_netstring(base64.standard_b64encode(
        hmac.new(config.ACCESSKEY, s, hashlib.sha256).digest()))

def send_message(message, mac):
    # Law of Demeter? Hahahahaha
    date = netstring.encode_netstring(datetime.datetime.utcnow()
            .replace(microsecond=0).isoformat().encode('ascii'))
    strtosign = (netstring.encode_netstring(message)
                 + netstring.encode_netstring(mac.rawstr().encode('ascii'))
                 + date)
    strtosend = netstring.encode_netstring(hmac_netstring(strtosign)
                                           + strtosign)
    sock = socket.create_connection((config.ACCESSHOST, config.ACCESSPORT),
                                    config.ACCESSTIMEOUT)
    try:
        sock.settimeout(config.ACCESSTIMEOUT)
        sock.sendall(strtosend)
        resp = sock.recv(256)
        (resp, _) = netstring.consume_netstring(resp)
        if resp != b'OK':
            raise Exception('Error sending message {0!r}: {1!r}'
                            .format(strtosend, resp))
    finally:
        sock.close()

def authorize(mac):
    send_message(b'grant', mac)

def revoke(mac):
    send_message(b'revoke', mac)
