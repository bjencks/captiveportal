class MAC:
    def __init__(self, inp):
        if isinstance(inp, bytes):
            if len(inp) == 6:
                self.bytes = inp
            else:
                raise ValueError('Invalid bytestring length: ' + str(len(inp)))
        elif isinstance(inp, str):
            self.bytes = _mac_str_to_bytes(inp)
    def rawstr(self):
        return ''.join(['{0:02x}'.format(x) for x in self.bytes])
    def __str__(self):
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
    for char in newstr:
        if char not in '0123456789abcdefABCDEF':
            raise ValueError('Invalid MAC address: "{0}" (bad char: {1})'.format(str_, char))
    return bytes([int(newstr[i:i+2], 16) for i in range(0, 11, 2)])
