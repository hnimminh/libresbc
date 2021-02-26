import traceback
import json
import copy

import redis
from fastapi import APIRouter, Request, Response
from fastapi.templating import Jinja2Templates

from configuration import (ESL_HOST, ESL_PORT, ESL_USER, ESL_SECRET,
                           MAX_CPS, MAX_ACTIVE_SESSION, FIRST_RTP_PORT, LAST_RTP_PORT,
                           REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD, SCAN_COUNT)

from utilities import logify, get_request_uuid, hashlistify


REDIS_CONNECTION_POOL = redis.BlockingConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD, 
                                                     decode_responses=True, max_connections=10, timeout=5)
rdbconn = redis.StrictRedis(connection_pool=REDIS_CONNECTION_POOL)                                                    
pipe = rdbconn.pipeline()

# api router declaration
fsxmlrouter = APIRouter()

# template location 
templates = Jinja2Templates(directory="templates/fsxml")

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------

@fsxmlrouter.get("/fsxmlapi/switch", include_in_schema=False)
def switch(request: Request, response: Response):
    try:
        result = templates.TemplateResponse("switch.j2.xml",
                                            {"request": request, "max_sessions":MAX_ACTIVE_SESSION, "sessions_per_second":MAX_CPS, "rtp_start_port":FIRST_RTP_PORT, "rtp_end_port":LAST_RTP_PORT},
                                            media_type="application/xml")
        response.status_code = 200
    except Exception as e:
        response.status_code, result = 500, str()
        logify(f"module=liberator, space=fsxmlapi, section=switch, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


@fsxmlrouter.get("/fsxmlapi/event-socket", include_in_schema=False)
def esl(request: Request, response: Response):
    try:
        result = templates.TemplateResponse("event-socket.j2.xml",
                                            {"request": request, "host": ESL_HOST, "port": ESL_PORT, "password": ESL_SECRET},
                                            media_type="application/xml")
        response.status_code = 200
    except Exception as e:
        response.status_code, result = 500, str()
        logify(f"module=liberator, space=fsxmlapi, section=event-socket, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@fsxmlrouter.get("/fsxmlapi/acl", include_in_schema=False)
def acl(request: Request, response: Response):
    try:
        KEYPATTERN = f'intcon:in:*'
        next, mainkeys = rdbconn.scan(0, KEYPATTERN, SCAN_COUNT)
        while next:
            next, tmpkeys = rdbconn.scan(next, KEYPATTERN, SCAN_COUNT)
            mainkeys += tmpkeys

        for mainkey in mainkeys:
            pipe.hget(mainkey, 'sip_ips')

        data = list()
        for detail in pipe.execute():
            if detail: data += hashlistify(detail)
        ip_addresses = set(data)

        result = templates.TemplateResponse("acl.j2.xml",
                                            {"request": request, "ip_addresses": ip_addresses},
                                            media_type="application/xml")
        response.status_code = 200
    except Exception as e:
        response.status_code, result = 500, str()
        logify(f"module=liberator, space=fsxmlapi, section=acl, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result