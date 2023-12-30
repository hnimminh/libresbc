#
# liberator:cfgapi.py
#
# The Initial Developer of the Original Code is
# Minh Minh <hnimminh at[@] outlook dot[.] com>
# Portions created by the Initial Developer are Copyright (C) the Initial Developer.
# All Rights Reserved.
#

import traceback
import json
import hashlib
import redis
import validators
from fastapi import APIRouter, Request, Response
from fastapi.templating import Jinja2Templates
from configuration import (NODEID, CLUSTERS, _BUILTIN_ACLS_, NODEID_CHANNEL,
                           CRC_CAPABILITY, CRC_PGSQL_HOST, CRC_PGSQL_PORT, CRC_PGSQL_DATABASE, CRC_PGSQL_USERNAME, CRC_PGSQL_PASSWORD,
                           REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD, SCAN_COUNT)
from utilities import logger, get_request_uuid, fieldjsonify, jsonhash, getaname, listify, randomstr


REDIS_CONNECTION_POOL = redis.BlockingConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD,
                                                     decode_responses=True, max_connections=10, timeout=5)
rdbconn = redis.StrictRedis(connection_pool=REDIS_CONNECTION_POOL)

# dynamic default sip passwd
SIP_DFTPASSWORD = randomstr(20)

# api router declaration
cfgrouter = APIRouter()

# template location
fstpl = Jinja2Templates(directory="fscfg/xml")

# call recovery settings
crcs = {
    'capability': CRC_CAPABILITY,
    'host': CRC_PGSQL_HOST,
    'port': CRC_PGSQL_PORT,
    'database': CRC_PGSQL_DATABASE,
    'username': CRC_PGSQL_USERNAME,
    'password': CRC_PGSQL_PASSWORD,
}
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
@cfgrouter.get("/cfgapi/fsxml/switch", include_in_schema=False)
def switch(request: Request, response: Response):
    try:
        result = fstpl.TemplateResponse("switch.j2.xml",
                                            {"request": request, "switchattributes": CLUSTERS, 'crcs': crcs},
                                            media_type="application/xml")
        response.status_code = 200
    except Exception as e:
        response.status_code, result = 500, str()
        logger.error(f"module=liberator, space=cfgapi, section=switch, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


@cfgrouter.get("/cfgapi/fsxml/acl", include_in_schema=False)
def acl(request: Request, response: Response):
    try:
        pipe = rdbconn.pipeline()
        # SIP PROFILE AND REALM
        profilenames = rdbconn.smembers('nameset:sipprofile')
        for profilename in profilenames:
            pipe.hget(f'sipprofile:{profilename}', 'realm' )
        realms = pipe.execute()
        sipprofiles = dict()
        for profilename, realm in zip(profilenames, realms):
            sipprofiles.update({profilename: realm})

        # ENGAGMENT ACL LIST
        # [{'name': name, 'action': default-action, 'rules': [{'action': allow/deny, 'key': domain/cidr, 'value': ip/domain-value}]}]
        for profilename in profilenames:
            pipe.hget(f'sipprofile:{profilename}', 'local_network_acl')
        engagedacls = [acl for acl in pipe.execute() if acl not in _BUILTIN_ACLS_]
        for engagedacl in engagedacls:
            pipe.hgetall(f'base:acl:{engagedacl}')
        details = pipe.execute()
        acls = list()
        for detail in details:
            if detail:
                name = detail.get('name')
                action = detail.get('action')
                rules = fieldjsonify(detail.get('rules'))
                acls.append({'name': name, 'action': action, 'rules': rules})

        result = fstpl.TemplateResponse("acl.j2.xml",
                                            {"request": request, "sipprofiles": sipprofiles, "acls": acls},
                                            media_type="application/xml")
        response.status_code = 200
    except Exception as e:
        response.status_code, result = 500, str()
        logger.error(f"module=liberator, space=cfgapi, section=acl, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


@cfgrouter.get("/cfgapi/fsxml/distributor", include_in_schema=False)
def distributor(request: Request, response: Response):
    try:
        pipe = rdbconn.pipeline()
        profilenames = rdbconn.smembers('nameset:sipprofile')
        for profilename in profilenames:
            pipe.smembers(f'engagement:sipprofile:{profilename}')
        intconsets = pipe.execute()
        intconnameids = [item for sublist in intconsets for item in sublist if item.startswith('out:')]
        for intconnameid in intconnameids:
            pipe.hgetall(f'intcon:{intconnameid}:_gateways')
        details = pipe.execute()

        interconnections = dict()
        for intconnameid, detail in zip(intconnameids, details):
            intconname = getaname(intconnameid)
            interconnections.update({intconname: jsonhash(detail)})

        result = fstpl.TemplateResponse("distributor.j2.xml",
                                            {"request": request, "interconnections": interconnections},
                                            media_type="application/xml")
        response.status_code = 200
    except Exception as e:
        response.status_code, result = 500, str()
        logger.info(f"module=liberator, space=cfgapi, section=distributor, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


@cfgrouter.get("/cfgapi/fsxml/sip-setting", include_in_schema=False)
def sip(request: Request, response: Response):
    try:
        pipe = rdbconn.pipeline()
        fsgvars = list()
        # get netalias
        netaliasnames = rdbconn.smembers('nameset:netalias')
        for netaliasname in netaliasnames:
            pipe.hget(f'base:netalias:{netaliasname}', 'addresses')
        details = pipe.execute()
        netaliases = dict()
        for netaliasname, detail in zip(netaliasnames, details):
            addresses = [address for address in fieldjsonify(detail) if address.get('member') == NODEID][0]
            netaliases.update({netaliasname: addresses})
        # get the maping siprofile and data
        # {profilename1: profiledata1, profilename2: profiledata2}
        profilenames = rdbconn.smembers('nameset:sipprofile')
        for profilename in profilenames:
            pipe.hgetall(f'sipprofile:{profilename}')
        details = pipe.execute()
        sipprofiles = dict()
        for profilename, detail in zip(profilenames, details):
            sipdetail = jsonhash(detail)
            sip_address = sipdetail.pop('sip_address')
            sip_ip = netaliases[sip_address]['listen']
            ext_sip_ip = netaliases[sip_address]['advertise']
            rtp_address = sipdetail.pop('rtp_address')
            rtp_ip = netaliases[rtp_address]['listen']
            ext_rtp_ip = netaliases[rtp_address]['advertise']
            sipdetail.update({'sip_ip': sip_ip, 'ext_sip_ip': ext_sip_ip, 'rtp_ip': rtp_ip, 'ext_rtp_ip': ext_rtp_ip})
            sipprofiles.update({profilename: sipdetail})
            # prepare vars
            fsgvars.append(f'{profilename}:advertising={ext_sip_ip}')

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
            for gateway in gateways:
                realm = gateway.get('realm')
                if realm and validators.ipv6(realm):
                    gateway['realm'] = f'[{realm}]'
                proxy = gateway.get('proxy')
                if proxy and validators.ipv6(proxy):
                    gateway['proxy'] = f'[{proxy}]'
                from_domain = gateway.get('from_domain')
                if from_domain and validators.ipv6(from_domain):
                    gateway['from_domain'] = f'[{from_domain}]'
                register_proxy = gateway.get('register_proxy')
                if register_proxy and validators.ipv6(register_proxy):
                    gateway['register_proxy'] = f'[{register_proxy}]'
            if gateways:
                sipprofiles[sipprofile]['gateways'] = gateways

        # set var profile address by separated thread
        rdbconn.publish(NODEID_CHANNEL, json.dumps({'portion': 'cfgapi:sip', 'delay': 30, 'fsgvars': fsgvars, 'requestid': get_request_uuid()}))
        # template
        result = fstpl.TemplateResponse("sip-setting.j2.xml",
                                            {"request": request, "sipprofiles": sipprofiles, 'crcs': crcs, 'NODEID': NODEID},
                                            media_type="application/xml")
        response.status_code = 200
    except Exception as e:
        response.status_code, result = 500, str()
        logger.error(f"module=liberator, space=cfgapi, section=sip-setting, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


@cfgrouter.get("/cfgapi/fsxml/directory", include_in_schema=False)
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
        intconnameids = [item for sublist in intconsets for item in sublist if item.startswith('in:')]
        for intconnameid in intconnameids:
            pipe.hmget(f'intcon:{intconnameid}', 'sipprofile', 'sipaddrs', 'secret', 'authscheme', 'routing', 'ringready')
        details = pipe.execute()

        directories = dict()
        for intconnameid, detail in zip(intconnameids, details):
            intconname = getaname(intconnameid)
            profilename = detail[0]
            sipaddrs = fieldjsonify(detail[1])
            secret = detail[2]
            authscheme = detail[3]
            routing = detail[4]
            ringready = fieldjsonify(detail[5])

            if authscheme=='IP':
                password = SIP_DFTPASSWORD
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
                    directory = {'id': intconname, 'cidrs': cidrs, 'a1hash': a1hash, 'routing': routing, 'ringready': ringready}
                    if _realm in directories: directories[_realm].append(directory)
                    else: directories[_realm] = [directory]

        result = fstpl.TemplateResponse("directory.j2.xml",
                                            {"request": request, "directories": directories},
                                            media_type="application/xml")
        response.status_code = 200
    except Exception as e:
        response.status_code, result = 500, str()
        logger.error(f"module=liberator, space=cfgapi, section=directory, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result
