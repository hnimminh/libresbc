import time
import uuid
import syslog
import traceback
import threading

import uvicorn
from fastapi import FastAPI, Request, Response, Depends, status

from configuration import _APPLICATION, _SWVERSION, _DESCRIPTION
from utilities import logger, dlogger, _request_uuid_ctx_var, get_request_uuid
from libreapi import librerouter


#----------------------------------------------------------------------------------------------------------------------
fastapi = FastAPI(title=_APPLICATION, version=_SWVERSION, description=_DESCRIPTION, docs_url=None, redoc_url='/documents')
#----------------------------------------------------------------------------------------------------------------------
# MIDDLEWARE
#----------------------------------------------------------------------------------------------------------------------
@fastapi.middleware('http')
async def tracking(request: Request, call_next) -> Response:
    try:
        start_time = time.time()
        request_uuid = _request_uuid_ctx_var.set(str(uuid.uuid4()))
        clientip = request.client.host
        rmethod = request.method
        rurl = request.url
        response = await call_next(request)
        process_time = round(time.time() - start_time, 3)
        logger(f'module=liberator, space=httpapi, action=midware, requestid={get_request_uuid()}, clientip={clientip}, request={rmethod}:{rurl}, processtime={process_time}')
        _request_uuid_ctx_var.reset(request_uuid)
        return response
    except:
        pass

async def reqjson(request: Request):
    try:
        reqbody = await request.json()
        logger(f'module=liberator, space=httpapi, action=depend, requestid={get_request_uuid()}, request={reqbody}')
    except:
        pass

#----------------------------------------------------------------------------------------------------------------------
# HEARTBEAT
#----------------------------------------------------------------------------------------------------------------------
@fastapi.get("/heartbeat")
def heartbeat():
    return "OK"
#----------------------------------------------------------------------------------------------------------------------
# ROUTER SEGMENTS API
# ------------------------------------------------------
fastapi.include_router(librerouter, dependencies=[Depends(reqjson)])
#fastapi.include_router(provisioning.router)

#----------------------------------------------------------------------------------------------------------------------
# MAIN APPLICATION
#----------------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    try:
        dlogger('module=liberator, space=main, action=liberator_starting')
        # HTTP API
        uvicorn.run('main:fastapi', host='127.0.0.1', port=8080, workers=4, )
    except Exception as e:
        logger(f'module=liberator, space=main, exception: {e}, traceback: {traceback.format_exc()}')
    finally:
        dlogger('module=liberator, space=main, action=liberator_stopping')
        for thrd in threading.enumerate():
            thrd.stop = True
            logger(f'module=liberator, space=main, action=thread_teardown, id={thrd.native_id}:{thrd.ident}, name={thrd.getName()}')
        syslog.closelog()

