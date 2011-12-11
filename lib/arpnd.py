# Copyright 2011 Ben Jencks
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import ipaddr
import subprocess
import logging
from mac import MAC

LOGGER = logging.getLogger('arpnd')

VALID_STATES = ('REACHABLE', 'DELAY', 'STALE')

def parse_ipneigh_line(line, cons):
    try:
        tokens = line.split()
        state = tokens[-1]
        if state not in VALID_STATES:
            return None
        ip = cons(tokens[0])
        mac = MAC(tokens[tokens.index('lladdr') + 1])
        return (mac, ip)
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
        return ipneigh[0]
    else:
        return None
