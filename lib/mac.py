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


class MAC:
    """Simple container for a MAC address, with parsing and formatting routines.

    """
    def __init__(self, inp):
        """Construct a MAC from either a bytes object (6 bytes) or a hex string
        in standard, Cisco, or non-delimited format.
        
        """
        if isinstance(inp, bytes):
            if len(inp) == 6:
                self.bytes = inp
            else:
                raise ValueError('Invalid bytestring length: ' + str(len(inp)))
        elif isinstance(inp, str):
            self.bytes = _mac_str_to_bytes(inp)
    def rawstr(self):
        """Return a non-delimited hex representation of the address"""
        return ''.join(['{0:02x}'.format(x) for x in self.bytes])
    def __str__(self):
        """Return a representation of the address formatted in standard
        colon-delimited form.
        
        """
        return ':'.join(['{0:02x}'.format(x) for x in self.bytes])
    def __repr__(self):
        return 'MAC(\'{0}\')'.format(str(self))
    def __hash__(self):
        return self.bytes.__hash__()
    def __eq__(self, other):
        if isinstance(other, MAC):
            return other.bytes == self.bytes
        else:
            return False

def _mac_str_to_bytes(str_):
    newstr = str_.replace(':', '').replace('.', '')
    if len(newstr) != 12:
        raise ValueError('Invalid MAC address: "{0}" (bad length: {1:s})'.format(str_, len(newstr)))
    return bytes.fromhex(newstr)
