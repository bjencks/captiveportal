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

import urllib.request
import urllib.parse
import common
import logging
import logging.handlers
import sys

SESSION_URL = 'http://vps.bjencks.net:8080/session'

LOGGER = logging.getLogger('session')

def submit_session(action=None, source=None, mac=None, ipv4=None, ipv6=None,
                   time=None, key=None):
    strmac = mac.rawstr()
    strtime = time.strftime('%Y-%m-%dT%H:%M:%S')
    params = {'action': action, 'source': source, 'mac': strmac, 'time': strtime}
    if ipv4:
        params['ipv4'] = str(ipv4)
    if ipv6:
        params['ipv6'] = str(ipv6)
    body = urllib.parse.urlencode(params).encode('ascii')
    params['key'] = key
    auth_header = common.gen_authorization_header(**params)
    req = urllib.request.Request(SESSION_URL, data=body)
    req.add_header('Authorization', auth_header)
    LOGGER.debug("Submitting session: %s (%s)", body, auth_header)
    urllib.request.urlopen(req)

def setup_logging(name):
    loghandler = logging.handlers.SysLogHandler('/dev/log',
                    logging.handlers.SysLogHandler.LOG_DAEMON)
    loghandler.setFormatter(logging.Formatter("{0}: (%(name)s) %(message)s".format(name)))
    stderrhandler = logging.StreamHandler()
    stderrhandler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(message)s'))
    rootlogger = logging.getLogger()
    #rootlogger.addHandler(loghandler)
    rootlogger.addHandler(stderrhandler)
    rootlogger.setLevel(logging.DEBUG)
    def exc_handler(typ, val, tb):
        rootlogger.critical("Exception occurred", exc_info=(typ, val, tb))

    sys.excepthook = exc_handler
    return rootlogger

