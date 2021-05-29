import traceback
import json
import copy
import hashlib

import redis
from fastapi import APIRouter, Request, Response
from fastapi.templating import Jinja2Templates

from configuration import (NODEID, CLUSTERS,
                           ESL_HOST, ESL_PORT, ESL_SECRET, DEFAULT_PASSWORD,
                           REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD, SCAN_COUNT)

from utilities import logify, get_request_uuid, fieldjsonify, jsonhash, getnameid, listify


REDIS_CONNECTION_POOL = redis.BlockingConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD, 
                                                     decode_responses=True, max_connections=10, timeout=5)
rdbconn = redis.StrictRedis(connection_pool=REDIS_CONNECTION_POOL)                                                    

# api router declaration
fsxmlrouter = APIRouter()

# template location 
templates = Jinja2Templates(directory="templates/fsxml")

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
@fsxmlrouter.get("/fsxmlapi/switch", include_in_schema=False)
def switch(request: Request, response: Response):
    try:
        result = templates.TemplateResponse("switch.j2.xml",
                                            {"request": request, "switchattributes": CLUSTERS},
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
        pipe = rdbconn.pipeline()
        # IP LIST OF SIP PROFILE AND REALM
        profilenames = rdbconn.smembers('nameset:sipprofile')
        for profilename in profilenames:
            pipe.hget(f'sipprofile:{profilename}', 'realm' )
        realms = pipe.execute()
        sipprofiles = dict()
        for profilename, realm in zip(profilenames, realms):
            sipprofiles.update({profilename: realm})

        # DEFINED ACL LIST
        # [{'name': name, 'action': default-action, 'rules': [{'action': allow/deny, 'key': domain/cidr, 'value': ip/domain-value}]}]
        KEYPATTERN = 'base:acl:*'
        next, mainkeys = rdbconn.scan(0, KEYPATTERN, SCAN_COUNT)
        while next:
            next, tmpkeys = rdbconn.scan(next, KEYPATTERN, SCAN_COUNT)
            mainkeys += tmpkeys
        for mainkey in mainkeys:
            pipe.hgetall(mainkey)
        defined_acls = list()
        for detail in pipe.execute():
            if detail:
                name = detail.get('name')
                action = detail.get('action')
                rulestrs = fieldjsonify(detail.get('rules'))
                rules = list(map(lambda rule: {'action': rule[0], 'key': rule[1], 'value': rule[2]}, map(listify, rulestrs)))
                defined_acls.append({'name': name, 'action': action, 'rules': rules})

        result = templates.TemplateResponse("acl.j2.xml",
                                            {"request": request, "sipprofiles": sipprofiles, "defined_acls": defined_acls},
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
        pipe = rdbconn.pipeline()
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
        pipe = rdbconn.pipeline()
        # get netalias
        # {profilename1: profiledata1, profilename2: profiledata2}
        KEYPATTERN = 'base:netalias:*'
        next, mainkeys = rdbconn.scan(0, KEYPATTERN, SCAN_COUNT)
        while next:
            next, tmpkeys = rdbconn.scan(next, KEYPATTERN, SCAN_COUNT)
            mainkeys += tmpkeys
        for mainkey in mainkeys:
            pipe.hget(mainkey, 'addresses')
        details = pipe.execute()
        netaliases = dict()
        for mainkey, detail in zip(mainkeys, details):
            aliasname = getnameid(mainkey)
            addresses = list(map(listify, fieldjsonify(detail)))
            netaliases[aliasname] = {address[0]: {'listen': address[1], 'advertise': address[2]} for address in addresses}

        # get the maping siprofile and data
        # {profilename1: profiledata1, profilename2: profiledata2}
        profilenames = rdbconn.smembers('nameset:sipprofile')
        for profilename in profilenames:
            pipe.hgetall(f'sipprofile:{profilename}')
        details = pipe.execute()
        sipprofiles = dict()
        for profilename, detail in zip(profilenames, details):
            sipprofiles.update({profilename: jsonhash(detail)})

        # get the mapping siprofile name and interconnection name
        # {profilename1: [intconname,...], profilename2: [intconname,...]}
        map_profilename_intconnames = {}
        for profilenames in sipprofiles.keys():
            intcon_names = rdbconn.smembers(f'engagement:sipprofile:{profilenames}')
            out_intcon_names = list(filter(lambda name: name.startswith('out:') ,intcon_names))
            map_profilename_intconnames[profilenames] = out_intcon_names

        # get the mapping siprofile name and gateway name
        # {profilename1: [gateway,...], profilename2: [gateway,...]}
        map_profilename_gwnames = dict()
        for profilename, intcons in map_profilename_intconnames.items():
            for intcon in intcons:
                pipe.hkeys(f'intcon:{intcon}:_gateways')
            allgws = pipe.execute()
            map_profilename_gwnames[profilename] = list(set([gw for gws in allgws for gw in gws]))

        # add gateway data to sip profile data
        map_profilename_gateways = dict()
        for profilename, gwnames in map_profilename_gwnames.items():
            for gwname in gwnames:
                pipe.hgetall(f'base:gateway:{gwname}')
            map_profilename_gateways[profilename] = list(filter(lambda gwdata: gwdata, map(jsonhash, pipe.execute())))
        for sipprofile in sipprofiles:
            gateways = map_profilename_gateways.get(sipprofile)
            if gateways:
                sipprofiles[sipprofile]['gateways'] = gateways

        # template
        result = templates.TemplateResponse("sip-setting.j2.xml",
                                            {"request": request, "sipprofiles": sipprofiles, 'netaliases': netaliases, 'NODEID': NODEID},
                                            media_type="application/xml")
        response.status_code = 200
    except Exception as e:
        response.status_code, result = 500, str()
        logify(f"module=liberator, space=fsxmlapi, section=sip-setting, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


@fsxmlrouter.get("/fsxmlapi/directory", include_in_schema=False)
def directory(request: Request, response: Response):
    try:
        pipe = rdbconn.pipeline()
        # IP LIST OF SIP PROFILE AND REALM
        profilenames = rdbconn.smembers('nameset:sipprofile')
        for profilename in profilenames:
            pipe.hget(f'sipprofile:{profilename}', 'realm' )
        realms = pipe.execute()
        sipprofiles = dict()
        for profilename, realm in zip(profilenames, realms):
            sipprofiles.update({profilename: realm})

        # IP LIST OF INBOUND INTERCONNECTION
        # {profilename: {profilename, sipaddrs, secret}}
        for profilename in profilenames:
            pipe.smembers(f'engagement:sipprofile:{profilename}')
        intconsets = pipe.execute()
        intconnames = [item for sublist in intconsets for item in sublist if item.startswith('in:')]
        for intconname in intconnames:
            pipe.hmget(f'intcon:{intconname}', 'sipprofile', 'sipaddrs', 'secret', 'authscheme', 'routing')
        details = pipe.execute()

        directories = dict()
        for intconname, detail in zip(intconnames, details):
            profilename = detail[0]
            sipaddrs = fieldjsonify(detail[1])
            secret = detail[2]
            authscheme = detail[3]
            routing = detail[4]

            if authscheme=='IP': 
                password = DEFAULT_PASSWORD
                cidrs = sipaddrs
            elif authscheme=='DIGEST': 
                password = secret
                cidrs = list()
            else:
                password = secret
                cidrs = sipaddrs

            for _profilename, _realm in sipprofiles.items():
                if _profilename == profilename:
                    a1hash = hashlib.md5(f'{intconname}:{_realm}:{password}'.encode()).hexdigest()
                    if _realm in directories: directories[_realm].append({'id': intconname, 'cidrs': cidrs, 'a1hash': a1hash, 'routing': routing})
                    else: directories[_realm] = [{'id': intconname, 'cidrs': cidrs, 'a1hash': a1hash, 'routing': routing}]

        result = templates.TemplateResponse("directory.j2.xml",
                                            {"request": request, "directories": directories},
                                            media_type="application/xml")
        response.status_code = 200
    except Exception as e:
        response.status_code, result = 500, str()
        logify(f"module=liberator, space=fsxmlapi, section=directory, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result
