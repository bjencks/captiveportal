import ipaddr
import subprocess
import logging
from mac import MAC

LOGGER = logging.getLogger('arpnd')

VALID_STATES = ('REACHABLE', 'DELAY', 'STALE')

def parse_ipneigh_line(line, cons):
    try:
        tokens = line.split()
        ip = cons(tokens[0])
        mac = MAC(tokens[tokens.index('lladdr') + 1])
        state = tokens[-1]
        if state not in VALID_STATES:
            return None
        return (ip, mac)
    except:
        LOGGER.exception("Failed to parse line {0!r}".format(line))
        return None

def get_current_sessions(version, device):
    """Returns a set of ARP entries, represented as (MAC, IPv4Address) pairs.

    """
    if version == 4:
        arg = '-4'
        cons = ipaddr.IPv4Address
    elif version == 6:
        arg = '-6'
        cons = ipaddr.IPv6Address
    p = subprocess.Popen(('/bin/ip', arg, 'neigh', 'show', 'dev', device), stdout=subprocess.PIPE)
    (out, _) = p.communicate()
    neighs = (parse_ipneigh_line(line, cons) for line in out.decode('ascii').splitlines())
    return [neigh for neigh in neighs if neigh]

def get_mac_for_addr(addr):
    p = subprocess.Popen(('/bin/ip', 'neigh', 'show', str(addr)), stdout=subprocess.PIPE)
    (out, _) = p.communicate()
    lines = out.decode('ascii').splitlines()
    if len(lines) == 0:
        return None
    if len(lines) > 1:
        LOGGER.warning('More than one result for {0!r}'.format(addr))
    ipneigh = parse_ipneigh_line(lines[0], addr.__class__)
    if ipneigh:
        return ipneigh[1]
    else:
        return None
