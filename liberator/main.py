#
# liberator:main.py
#
# The Initial Developer of the Original Code is
# Minh Minh <hnimminh at[@] outlook dot[.] com>
# Portions created by the Initial Developer are Copyright (C) the Initial Developer.
# All Rights Reserved.
#

import time
import uuid
import syslog
import traceback
import threading

import uvicorn

from configuration import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_DB, NODEID, HTTPCDR_ENDPOINTS, DISKCDR_ENABLE, CDRFNAME_INTERVAL, CDRFNAME_FMT
from utilities import logify, debugy
from api import httpapi
from basemgr import BaseEventHandler, SecurityEventHandler, basestartup
from cdr import CDRMaster

#---------------------------------------------------------------------------------------------------------------------------
# MAIN APPLICATION
#---------------------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    try:
        debugy(f'''module=liberator, space=main, action=initialize, REDIS_HOST={REDIS_HOST}, REDIS_PORT={REDIS_PORT}'''
               f''', REDIS_PASSWORD={str(REDIS_PASSWORD)[:3]}*, REDIS_DB={REDIS_DB}, NODEID={NODEID}, HTTPCDR_ENDPOINTS={HTTPCDR_ENDPOINTS}'''
               f''', DISKCDR_ENABLE={DISKCDR_ENABLE}, CDRFNAME_INTERVAL={CDRFNAME_INTERVAL}, CDRFNAME_FMT={CDRFNAME_FMT}'''
            )
        # EVENT HANDLER
        basestartup()
        eventthead = BaseEventHandler()
        eventthead.start()
        secthread = SecurityEventHandler()
        secthread.start()
        # CDR HANDLER
        cdrthread = CDRMaster()
        cdrthread.start()
        # HTTP API
        uvicorn.run('api:httpapi', host='127.0.0.1', port=8080, workers=4, access_log=False)
    except Exception as e:
        logify(f'module=liberator, space=main, exception: {e}, traceback: {traceback.format_exc()}')
    finally:
        debugy('module=liberator, space=main, action=liberator_stopping')
        for thrd in threading.enumerate():
            thrd.stop = True
            logify(f'module=liberator, space=main, action=teardown, id={thrd.ident}, name={thrd.getName()}')
        syslog.closelog()

