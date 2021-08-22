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

from utilities import logify, debugy
from api import httpapi
from basemgr import BaseEventHandler, SecurityEventHandler, basestartup
from cdr import CDRMaster

#---------------------------------------------------------------------------------------------------------------------------
# MAIN APPLICATION
#---------------------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    try:
        debugy('module=liberator, space=main, action=initialize')
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

