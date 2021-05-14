import time
import uuid
import syslog
import traceback
import threading

import uvicorn

from utilities import logify, debugy
from api import httpapi
from basemgr import BaseEventHandler

#---------------------------------------------------------------------------------------------------------------------------
# MAIN APPLICATION
#---------------------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    try:
        debugy('module=liberator, space=main, action=initialize')
        # EVENT HANDLER
        eventthead = BaseEventHandler()
        eventthead.start()
        # HTTP API
        uvicorn.run('api:httpapi', host='127.0.0.1', port=8080, workers=4, reload=True )
    except Exception as e:
        logify(f'module=liberator, space=main, exception: {e}, traceback: {traceback.format_exc()}')
    finally:
        debugy('module=liberator, space=main, action=liberator_stopping')
        for thrd in threading.enumerate():
            thrd.stop = True
            logify(f'module=liberator, space=main, action=teardown, id={thrd.ident}, name={thrd.getName()}')
        syslog.closelog()

