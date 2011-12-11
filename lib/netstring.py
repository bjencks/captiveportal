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

def encode_netstring(s):
    return str(len(s)).encode('ascii') + b':' + s + b','

def consume_netstring(s):
    """If s is a bytestring beginning with a netstring, returns (value, rest)
    where value is the contents of the netstring, and rest is the part of s
    after the netstring.
    
    Raises ValueError if s does not begin with a netstring.
    
    """
    (length, sep, rest) = s.partition(b':')
    if sep != b':':
        raise ValueError("No colon found in s")
    if not length.isdigit():
        raise ValueError("Length is not numeric")
    length = int(length)
    if len(rest) <= length:
        raise ValueError("String not long enough")
    if rest[length] != 0x2c:
        raise ValueError("String not terminated with comma")
    return (rest[:length], rest[length+1:])

def is_netstring(s):
    try:
        (val, rest) = consume_netstring(s)
        return len(rest) == 0
    except ValueError:
        return False
