#
# liberator:main.py
#
# The Initial Developer of the Original Code is
# Minh Minh <hnimminh at[@] outlook dot[.] com>
# Portions created by the Initial Developer are Copyright (C) the Initial Developer.
# All Rights Reserved.
#

import traceback
import threading
import uvicorn
from configuration import (
    REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, REDIS_DB, HTTPCDR_ENDPOINTS, DISKCDR_ENABLE, CDRFNAME_INTERVAL, CDRFNAME_FMT,
    HTTP_API_LISTEN_IP, HTTP_API_LISTEN_PORT,
)
from utilities import logger
from basemgr import BaseEventHandler, SecurityEventHandler, basestartup
from cdr import CDRMaster

#---------------------------------------------------------------------------------------------------------------------------
# MAIN APPLICATION
#---------------------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    try:
        logger.debug(
            f'''module=liberator, space=main, action=initialize, REDIS_HOST={REDIS_HOST}, REDIS_PORT={REDIS_PORT}'''
            f''', REDIS_PASSWORD={str(REDIS_PASSWORD)[:3]}*, REDIS_DB={REDIS_DB}, HTTPCDR_ENDPOINTS={HTTPCDR_ENDPOINTS}'''
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
        uvicorn.run('api:httpapi', host=HTTP_API_LISTEN_IP, port=HTTP_API_LISTEN_PORT, workers=4, access_log=False)
    except Exception as e:
        logger.critical(f'module=liberator, space=main, exception: {e}, traceback: {traceback.format_exc()}')
    finally:
        logger.debug('module=liberator, space=main, action=liberator_stopping')
        for thrd in threading.enumerate():
            thrd.stop = True
            logger.info(f'module=liberator, space=main, action=teardown, id={thrd.ident}, name={thrd.name}')
