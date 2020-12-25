import time
import uuid
import syslog
import traceback
import threading

import uvicorn
from fastapi import FastAPI, Request, Response, Depends, status

from configuration import _APPLICATION, _SWVERSION, _DESCRIPTION
from utilities import logify, debugy, _request_uuid_ctx_var, get_request_uuid
from libreapi import librerouter


#----------------------------------------------------------------------------------------------------------------------
fastapi = FastAPI(title=_APPLICATION, version=_SWVERSION, description=_DESCRIPTION, docs_url=None, redoc_url='/apidocs')
#----------------------------------------------------------------------------------------------------------------------
# MIDDLEWARE
#----------------------------------------------------------------------------------------------------------------------
@fastapi.middleware('http')
async def tracking(request: Request, call_next) -> Response:
    try:
        start_time = time.time()
        request_uuid = _request_uuid_ctx_var.set(str(uuid.uuid4()))
        clientip = request.client.host
        method = request.method.lower()
        url = request.url.path
        response = await call_next(request)
        status_code = response.status_code
        response_headers = dict(response.headers)
        response_media_type = response.media_type
        response_body = bytes()
        async for chunk in response.body_iterator: response_body += chunk
        response_body = response_body.decode()
        process_time = round(time.time() - start_time, 3)
        if url.startswith('/libresbc/'): logify(f'module=liberator, space=httpapi, action=middleware, processtime={process_time}, requestid={get_request_uuid()}, clientip={clientip}, request={method}:{url}, status_code={status_code}, response_body={response_body}')
        else: logify(f'module=liberator, space=httpapi, action=middleware, processtime={process_time}, requestid={get_request_uuid()}, clientip={clientip}, request={method}:{url}, status_code={status_code}')
        _request_uuid_ctx_var.reset(request_uuid)
        return Response(content=response_body,
                        status_code=status_code,
                        headers=response_headers,
                        media_type=response_media_type)
    except:
        pass

async def reqjson(request: Request):
    try:
        reqbody = await request.json()
        logify(f'module=liberator, space=httpapi, action=request, requestid={get_request_uuid()}, request_body={reqbody}')
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
        debugy('module=liberator, space=main, action=initialize')
        # HTTP API
        uvicorn.run('main:fastapi', host='127.0.0.1', port=8080, workers=4, reload=True )
    except Exception as e:
        logify(f'module=liberator, space=main, exception: {e}, traceback: {traceback.format_exc()}')
    finally:
        debugy('module=liberator, space=main, action=liberator_stopping')
        for thrd in threading.enumerate():
            thrd.stop = True
            logify(f'module=liberator, space=main, action=teardown, id={thrd.ident}, name={thrd.getName()}')
        syslog.closelog()

