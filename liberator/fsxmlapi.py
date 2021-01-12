import traceback
import json
import copy

import redis
from fastapi import APIRouter, Request, Response
from fastapi.templating import Jinja2Templates

from configuration import (ESL_HOST, ESL_PORT, ESL_USER, ESL_SECRET,
                           MAX_SPS, MAX_SESSION, FIRST_RTP_PORT, LAST_RTP_PORT,
                           REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD, SCAN_COUNT)

from utilities import logify, get_request_uuid


# api router declaration
fsxmlrouter = APIRouter()

# template location 
templates = Jinja2Templates(directory="templates/fsxml")

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------

@fsxmlrouter.get("/fsxmlapi/switch", include_in_schema=False)
def switch(request: Request, response: Response):
    try:
        result = templates.TemplateResponse("switch.j2.xml",
                                            {"request": request, "max_sessions":MAX_SESSION, "sessions_per_second":MAX_SPS, "rtp_start_port":FIRST_RTP_PORT, "rtp_end_port":LAST_RTP_PORT},
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
        result = templates.TemplateResponse("switch.j2.xml",
                                            {"request": request, "host": ESL_HOST, "port": ESL_PORT, "password": ESL_SECRET},
                                            media_type="application/xml")
        response.status_code = 200
    except Exception as e:
        response.status_code, result = 500, str()
        logify(f"module=liberator, space=fsxmlapi, section=event-socket, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

