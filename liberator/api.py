#
# liberator:api.py
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

from fastapi import FastAPI, Request, Response, Depends, status

from configuration import _APPLICATION, _SWVERSION, _DESCRIPTION
from utilities import logify, debugy, _request_uuid_ctx_var, get_request_uuid
from libreapi import librerouter
from cfgapi import cfgrouter

#---------------------------------------------------------------------------------------------------------------------------
httpapi = FastAPI(title=_APPLICATION, version=_SWVERSION, description=_DESCRIPTION, docs_url=None, redoc_url='/apidocs')
#---------------------------------------------------------------------------------------------------------------------------
# MIDDLEWARE
#---------------------------------------------------------------------------------------------------------------------------
@httpapi.middleware('http')
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
        if url.startswith('/libreapi/'):
            logify(f'module=liberator, space=httpapi, action=middleware, processtime={process_time}, requestid={get_request_uuid()}, clientip={clientip}, request={method}:{url}, status_code={status_code}, response_body={response_body}')
        else:
            logify(f'module=liberator, space=httpapi, action=middleware, processtime={process_time}, requestid={get_request_uuid()}, clientip={clientip}, request={method}:{url}, status_code={status_code}')
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

#---------------------------------------------------------------------------------------------------------------------------
# HEARTBEAT
#---------------------------------------------------------------------------------------------------------------------------
@httpapi.get("/heartbeat")
def heartbeat():
    return "OK"
#---------------------------------------------------------------------------------------------------------------------------
# ROUTER SEGMENTS API
# ------------------------------------------------------
httpapi.include_router(librerouter, dependencies=[Depends(reqjson)])
httpapi.include_router(cfgrouter)
