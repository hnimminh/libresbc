import traceback
import json
import copy

import redis
from fastapi import APIRouter, Request, Response
from fastapi.templating import Jinja2Templates

from configuration import (ESL_HOST, ESL_PORT, ESL_SECRET,
                           MAX_SPS, MAX_SESSION, FIRST_RTP_PORT, LAST_RTP_PORT,
                           REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD, SCAN_COUNT)

from utilities import logify, get_request_uuid, hashlistify, jsonhash, getnameid


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
                                            {"request": request, "max_sessions": MAX_SESSION, "sessions_per_second": MAX_SPS, "rtp_start_port": FIRST_RTP_PORT, "rtp_end_port": LAST_RTP_PORT},
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
        KEYPATTERN = 'intcon:in:*'
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


@fsxmlrouter.get("/fsxmlapi/distributor", include_in_schema=False)
def distributor(request: Request, response: Response):
    try:
        KEYPATTERN = 'intcon:out:*:_gateways'
        next, mainkeys = rdbconn.scan(0, KEYPATTERN, SCAN_COUNT)
        while next:
            next, tmpkeys = rdbconn.scan(next, KEYPATTERN, SCAN_COUNT)
            mainkeys += tmpkeys

        for mainkey in mainkeys:
            pipe.hgetall(mainkey)
        details = pipe.execute()

        interconnections = dict()
        for mainkey, detail in zip(mainkeys, details):
            intconname = getnameid(mainkey)
            interconnections[intconname] = jsonhash(detail)

        result = templates.TemplateResponse("distributor.j2.xml",
                                            {"request": request, "interconnections": interconnections},
                                            media_type="application/xml")
        response.status_code = 200
    except Exception as e:
        response.status_code, result = 500, str()
        logify(f"module=liberator, space=fsxmlapi, section=distributor, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


@fsxmlrouter.get("/fsxmlapi/sip-setting", include_in_schema=False)
def sip(request: Request, response: Response):
    try:
        KEYPATTERN = 'sipprofile:*'
        next, mainkeys = rdbconn.scan(0, KEYPATTERN, SCAN_COUNT)
        while next:
            next, tmpkeys = rdbconn.scan(next, KEYPATTERN, SCAN_COUNT)
            mainkeys += tmpkeys

        for mainkey in mainkeys:
            pipe.hgetall(mainkey)
        details = pipe.execute()

        sipprofiles = dict()
        for mainkey, detail in zip(mainkeys, details):
            sipprofiles[getnameid(mainkey)] = jsonhash(detail)

        logify(f'sipprofiles {sipprofiles}')

        KEYPATTERN = 'intcon:out:*[^:]*'
        next, mainkeys = rdbconn.scan(0, KEYPATTERN, SCAN_COUNT)
        while next:
            next, tmpkeys = rdbconn.scan(next, KEYPATTERN, SCAN_COUNT)
            mainkeys += tmpkeys

        for mainkey in mainkeys:
            pipe.hget(mainkey, 'sipprofile')
        profilenames = pipe.execute()

        profile_intcons_maps = dict()
        for mainkey, profilename in zip(mainkeys, profilenames):
            intconname = getnameid(mainkey)
            if profilename not in profile_intcons_maps:
                profile_intcons_maps[profilename] = [intconname]
            else:
                if profilename not in profile_intcons_maps[profilename]:
                    profile_intcons_maps[profilename].append(profilename)

        logify(f'profile_intcons_maps {profile_intcons_maps}')

        profile_gwnames_maps = dict()
        for profile, intcons in profile_intcons_maps.items():
            for intcon in intcons:
                pipe.hkeys(f'intcon:out:{intcon}:_gateways')
            profile_gwnames_maps[profile] = list(set(pipe.execute()))

        logify(f'profile_gwnames_maps {profile_gwnames_maps}')

        profile_gateways_maps = dict()
        for profile, gwnames in profile_gwnames_maps.items():
            for gwname in gwnames:
                pipe.hgetall(f'gateway:{gwname}')
            profile_gateways_maps[profile] = list(map(jsonhash, pipe.execute()))

        logify(f'profile_gateways_maps {profile_gateways_maps}')

        for sipprofile in sipprofiles:
            sipprofiles[sipprofile]['gateways'] = profile_gateways_maps[sipprofile]

        logify(f'{sipprofiles}')

        # template
        result = templates.TemplateResponse("sip-setting.j2.xml",
                                            {"request": request, "sipprofiles": sipprofiles},
                                            media_type="application/xml")
        response.status_code = 200
    except Exception as e:
        response.status_code, result = 500, str()
        logify(f"module=liberator, space=fsxmlapi, section=sip-setting, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------

