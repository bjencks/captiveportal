
import hmac
import hashlib
import base64
import ipaddr

def gen_authorization_header(action=None, source=None, mac=None, ipv4=None,
                             ipv6=None, time=None, key=None):
    params = [action, source, mac, ipv4, ipv6, time]
    if not params[3]:
        params[3] = ''
    if not params[4]:
        params[4] = ''
    str_to_sign = ('\n'.join(params) + '\n').encode('ascii')
    sig = hmac.new(key, str_to_sign, hashlib.sha256).digest()
    return 'HMAC-SHA256 ' + base64.standard_b64encode(sig).decode('ascii')

def ipv4_to_bytes(addr):
    if addr is None:
        return None
    else:
        return addr.packed
def ipv6_to_bytes(addr):
    if addr is None:
        return None
    else:
        return addr.packed
def bytes_to_ipv4(by):
    if by is None:
        return None
    else:
        return ipaddr.IPv4Address(by)
def bytes_to_ipv6(by):
    if by is None:
        return None
    else:
        return ipaddr.IPv6Address(by)
