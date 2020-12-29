import traceback
import re
import json

import redis
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from enum import Enum
from ipaddress import IPv4Address, IPv4Network
from fastapi import APIRouter, Request, Response

from configuration import (_APPLICATION, _SWVERSION, _DESCRIPTION, _DEFAULT_NODENAME, _DEFAULT_CLUSTERNAME, 
                           NODEID, NODENAME, CLUSTERNAME, CLUSTERMEMBERS,
                           SWCODECS, MAX_CPS, MAX_ACTIVE_SESSION, 
                           REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD, SCAN_COUNT)
from utilities import logify, debugy, get_request_uuid, int2bool, bool2int, humanrid


REDIS_CONNECTION_POOL = redis.BlockingConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD, 
                                                     decode_responses=True, max_connections=10, timeout=5)
rdbconn = redis.StrictRedis(connection_pool=REDIS_CONNECTION_POOL)                                                    
pipe = rdbconn.pipeline()

# PATTERN
_NAME_ = '^[a-zA-Z][a-zA-Z0-9_]+$'; _NAME_PATTERN = re.compile(_NAME_)
_DIAL_ = '^[a-zA-Z0-9+#*]*$'; _DIAL_PATTERN = re.compile(_DIAL_)

# API ROUTER DECLARATION
librerouter = APIRouter()
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# INITIALIZE
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
try:
    NODENAME = rdbconn.get(f'cluster:node:{NODEID}')
    CLUSTERNAME = rdbconn.get('cluster:name')
    CLUSTERMEMBERS = rdbconn.smembers('cluster:members')
except:
    NODENAME = _DEFAULT_NODENAME
    CLUSTERNAME = _DEFAULT_CLUSTERNAME
    CLUSTERMEMBERS = [NODEID]

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# PREDEFINED INFORMATION
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
@librerouter.get("/libresbc/predefine", status_code=200)
def predefine():
    return {
        "nodename": NODENAME,
        "cluster": {
            "name": CLUSTERNAME,
            "members": CLUSTERMEMBERS
        },
        "application": _APPLICATION,
        'swversion': _SWVERSION,
        "description": _DESCRIPTION
    }

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# FUNDAMENTAL: CLUSTER NAME, NODE MEMBER
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
class NodeModel(BaseModel):
    nodeid: str = Field(max_length=32, description='The unique id of libresbc node')
    nodename: Optional[str] = Field(default=_DEFAULT_NODENAME, regex=_NAME_, max_length=32, description='The friendly name of libresbc node')

class ClusterModel(BaseModel):
    name: str = Field(regex=_NAME_, max_length=32, description='The name of libresbc cluster')
    members: List[NodeModel] = Field(min_items=1, max_item=16, description='The member of libresbc cluster')


@librerouter.put("/libresbc/cluster", status_code=200)
def update_cluster(reqbody: ClusterModel, response: Response):
    result = None
    try:
        name = reqbody.name
        members = reqbody.members
        _memberdata = rdbconn.hgetall('cluster:members')
        _nodeids = set(_memberdata.keys())
        memberdata = dict()
        nodeids = set()
        for member in members:
            nodename = member.nodename
            nodeid = member.nodeid
            nodeids.add(nodeid)
            memberdata.update({nodeid: nodename})
        
        oldids = _nodeids - nodeids
        for oldid in oldids:
            if rdbconn.scard(f'engagement:node:{oldid}'):
                response.status_code, result = 403, {'error': 'engaged_node'}; return

        pipe.set('cluster:name', name)
        pipe.hmset('cluster:members', memberdata)
        pipe.execute()
        CLUSTERNAME, CLUSTERMEMBERS = name, nodeids
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=change_cluster, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


@librerouter.get("/libresbc/cluster", status_code=200)
def get_cluster(response: Response):
    result = None
    try:
        name = rdbconn.get('cluster:name')
        memberdata = rdbconn.hgetall('cluster:members')
        members = [{'nodeid': nodeid, 'nodename': nodename} for nodeid, nodename in  memberdata.items()]
        response.status_code, result = 200, {'name': name, 'members': members}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=get_cluster, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result
#--------------------------------------------------------------------------------------------
@librerouter.post("/libresbc/node", status_code=200)
def declare_node(reqbody: NodeModel, response: Response):
    result = None
    try:
        id = reqbody.id
        name = reqbody.name
        rdbconn.set(f'node:{id}', name)
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=declare_node, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.delete("/libresbc/node", status_code=200)
def delete_node(reqbody: NodeModel, response: Response):
    result = None
    try:
        id = reqbody.id
        if rdbconn.sismember('cluster:members', id):
            response.status_code, result = 403, {'error': 'node_is_a_cluster_member'}; return
        if rdbconn.scard(f'engagement:node:{id}'):
            response.status_code, result = 403, {'error': 'engaged_node'}; return
        key = f'cluster:node:{id}'
        if not rdbconn.exists(key): 
            response.status_code, result = 400, {'error': 'nonexistent node'}; return
        rdbconn.delete(key)
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=delete_node, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libresbc/cluster/node/{nodeid}", status_code=200)
def detail_node(nodeid: str, response: Response):
    result = None
    try:
        key = f'cluster:node:{nodeid}'
        if not rdbconn.exists(key): 
            response.status_code, result = 400, {'error': 'nonexistent node'}; return
        name = rdbconn.get(key)
        clustered = True if rdbconn.sismember('cluster:members', nodeid) else False
        engagements = set(rdbconn.smembers('engagement:node:{nodeid}') + rdbconn.smembers('engagement:node:_ALL_'))
        response.status_code, result = 200, {'id': id, 'name': name, 'clustered': clustered, 'engagements': engagements}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=detail_node, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libresbc/cluster/node", status_code=200)
def list_node(response: Response):
    result = None
    try:
        KEYPATTERN = f'cluster:node:*'
        next, mainkeys = rdbconn.scan(0, KEYPATTERN, SCAN_COUNT)
        while next:
            next, tmpkeys = rdbconn.scan(next, KEYPATTERN, SCAN_COUNT)
            mainkeys += tmpkeys

        for mainkey in mainkeys:
            pipe.get(mainkey)
        names = pipe.execute()

        data = list()
        for mainkey, name in zip(mainkeys, names):
            id = mainkey.split(':')[-1]
            data.append({'id': id, 'name': name})

        response.status_code, result = 200, data
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=list_node, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# SIP PROFILES 
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
class SIPProfileModel(BaseModel):
    name: str = Field(regex=_NAME_, max_length=32, description='friendly name of sip profile')
    desc: str = Field(max_length=64, description='description')
    user_agent: str = Field(default='LibreSBC', max_length=64, description='Value that will be displayed in SIP header User-Agent')
    disable_transfer: bool = Field(default=False, description='true mean disable call transfer')
    manual_redirect: bool = Field(default=False, description='how call forward handled, true mean it be controlled under libresbc contraints, false mean it be work automatically')
    disable_hold: bool = Field(default=False, description='no handling the SIP re-INVITE with hold/unhold')
    nonce_ttl: int = Field(default=60, ge=15, le=120, description='TTL for nonce in sip auth')
    nat_space: str = Field(default='rfc1918.auto', description='the network will be applied NAT')
    sip_options_respond_503_on_busy: bool = Field(default=True, description='response 503 when system is in heavy load')
    enable_100rel: bool = Field(default=True, description='Reliability - PRACK message as defined in RFC3262')
    enable_timer: bool = Field(default=True, description='true to support for RFC 4028 SIP Session Timers')
    session_timeout: int = Field(default=0, ge=1800, le=3600, description='call to expire after the specified seconds')
    minimum_session_expires: int = Field(default=120, ge=90, le=3600, description='Value of SIP header Min-SE')
    sip_listen_port: int = Field(default=5060, ge=0, le=65535, description='Port to bind to for SIP traffic')
    sip_listen_ip: IPv4Address = Field(description='IP to bind to for SIP traffic')
    sip_advertising_ip: IPv4Address = Field(description='IP address that used to advertise to public network for SIP')
    rtp_listen_ip: IPv4Address = Field(description='IP to bind to for RTP traffic')
    rtp_advertising_ip: IPv4Address = Field(description='IP address that used to advertise to public network for RTP')
    sip_tls: bool = Field(default=False, description='true to enable SIP TLS')
    sips_port: int = Field(default=5061, ge=0, le=65535, description='Port to bind to for TLS SIP traffic')
    tls_version: List[str] = Field(default=['tlsv1.2'], description='TLS version')
    tls_cert_dir: str = Field(default='', description='TLS Certificate dirrectory')


@librerouter.post("/libresbc/sipprofile", status_code=200)
def create_sipprofile(reqbody: SIPProfileModel, response: Response):
    result = None
    try:
        data = reqbody.dict()
        nameid = humanrid.generate(); key = f'sipprofile:{nameid}'
        if rdbconn.exists(key): 
            response.status_code, result = 409, {'error': 'human readable id is not unique, please retry'}; return
        rdbconn.hmset(key, data)
        response.status_code, result = 200, {'nameid': nameid}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_sipprofile, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.put("/libresbc/sipprofile/{nameid}", status_code=200)
def update_sipprofile(reqbody: SIPProfileModel, nameid: str, response: Response):
    result = None
    try:
        data = reqbody.dict()
        key = f'sipprofile:{nameid}'
        if not rdbconn.exists(key): 
            response.status_code, result = 400, {'error': 'nonexistent sipprofile'}; return
        rdbconn.hmset(key, data)
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=update_sipprofile, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.delete("/libresbc/sipprofile/{nameid}", status_code=200)
def delete_sipprofile(nameid: str, response: Response):
    result = None
    try:
        if rdbconn.scard(f'engagement:sipprofile:{nameid}'): 
            response.status_code, result = 403, {'error': 'enageged sipprofile'}; return
        key = f'sipprofile:{nameid}'
        if not rdbconn.exists(key):
            response.status_code, result = 400, {'error': 'nonexistent sipprofile'}; return
        rdbconn.delete(key)
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=delete_sipprofile, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libresbc/sipprofile/{nameid}", status_code=200)
def detail_sipprofile(nameid: str, response: Response):
    result = None
    try:
        key = f'sipprofile:{nameid}'
        if not rdbconn.exists(key): 
            response.status_code, result = 400, {'error': 'nonexistent sipprofile'}; return
        data = rdbconn.hgetall(key)
        engagements = rdbconn.smembers(f'engagement:sipprofile:{nameid}')
        data.update({'engagements': engagements})
        response.status_code, result = 200, data
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=detail_sipprofile, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libresbc/sipprofile", status_code=200)
def list_sipprofile(response: Response):
    result = None
    try:
        KEYPATTERN = f'sipprofile:*'
        next, mainkeys = rdbconn.scan(0, KEYPATTERN, SCAN_COUNT)
        while next:
            next, tmpkeys = rdbconn.scan(next, KEYPATTERN, SCAN_COUNT)
            mainkeys += tmpkeys

        for mainkey in mainkeys:
            pipe.hmget(mainkey, 'name', 'desc')
        details = pipe.execute()

        data = list()
        for mainkey, detail in zip(mainkeys, details):
            if detail:
                nameid = mainkey.split(':')[-1]
                detail.update({'nameid': nameid})
                data.append(detail)

        response.status_code, result = 200, data
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=list_sipprofile, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# CODEC CLASS 
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
class CodecEnum(str, Enum):
    PCMA = "PCMA"
    PCMU = "PCMU"
    G729 = "G729"

class CodecModel(BaseModel):
    name: str = Field(regex=_NAME_, max_length=32, description='name of codec class')
    desc: str = Field(max_length=64, description='description')
    data: List[CodecEnum] = Field(min_items=1, max_item=len(SWCODECS), description='sorted set of codec')


@librerouter.post("/libresbc/class/codec", status_code=200)
def create_codec_class(reqbody: CodecModel, response: Response):
    result = None
    try:
        name = reqbody.name
        desc = reqbody.desc
        data = reqbody.data
        nameid = humanrid.generate(); key = f'class:codec:{nameid}'
        if rdbconn.exists(key):
            response.status_code, result = 409, {'error': 'human readable id is not unique, please retry'}; return
        rdbconn.hmset(key, {'name': name, 'desc': desc, 'data': json.dumps(data)})
        response.status_code, result = 200, {'nameid': nameid}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_codec_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.put("/libresbc/class/codec/{nameid}", status_code=200)
def update_codec_class(reqbody: CodecModel, nameid: str, response: Response):
    result = None
    try:
        name = reqbody.name
        desc = reqbody.desc
        data = reqbody.data
        key = f'class:codec:{nameid}'
        if not rdbconn.exists(key): 
            response.status_code, result = 400, {'error': 'nonexistent class'}; return
        rdbconn.hmset(key, {'name': name, 'desc': desc, 'data': json.dumps(data)})
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=update_codec_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.delete("/libresbc/class/codec/{nameid}", status_code=200)
def delete_codec_class(nameid: str, response: Response):
    result = None
    try:
        if rdbconn.scard(f'engagement:codec:{nameid}'): 
            response.status_code, result = 403, {'error': 'enageged class'}; return
        classkey = f'class:codec:{nameid}'
        if not rdbconn.exists(classkey):
            response.status_code, result = 400, {'error': 'nonexistent class'}; return
        rdbconn.delete(classkey)
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=delete_codec_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libresbc/class/codec/{nameid}", status_code=200)
def detail_codec_class(nameid: str, response: Response):
    result = None
    try:
        classkey = f'class:codec:{nameid}'
        if not rdbconn.exists(classkey): 
            response.status_code, result = 400, {'error': 'nonexistent class'}; return
        result = rdbconn.hgetall(classkey)
        result.update({'data': json.loads(result.get('data'))})
        engagements = rdbconn.smembers(f'engagement:codec:{nameid}')
        result.update({'engagements': engagements})
        response.status_code = 200
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=detail_codec_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libresbc/class/codec", status_code=200)
def list_codec_class(response: Response):
    result = None
    try:
        KEYPATTERN = f'class:codec:*'
        next, mainkeys = rdbconn.scan(0, KEYPATTERN, SCAN_COUNT)
        while next:
            next, tmpkeys = rdbconn.scan(next, KEYPATTERN, SCAN_COUNT)
            mainkeys += tmpkeys

        for mainkey in mainkeys:
            pipe.hmget(mainkey, 'name', 'desc')
        details = pipe.execute()

        data = list()
        for mainkey, detail in zip(mainkeys, details):
            if detail:
                data.append({'nameid': mainkey.split(':')[-1], 'name': detail[0], 'desc': detail[1]})

        response.status_code, result = 200, data
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=list_codec_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# CAPACITY 
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
class CapacityModel(BaseModel):
    name: str = Field(regex=_NAME_, max_length=32, description='name of capacity class')
    desc: str = Field(max_length=64, description='description')
    cps: int = Field(default=2, ge=1, le=len(CLUSTERMEMBERS)*MAX_CPS//2, description='call per second')
    cc: int = Field(default=10, ge=1, le=len(CLUSTERMEMBERS)*MAX_ACTIVE_SESSION//2, description='concurrent calls')


@librerouter.post("/libresbc/class/capacity", status_code=200)
def create_capacity_class(reqbody: CapacityModel, response: Response):
    result = None
    try:
        name = reqbody.name
        desc = reqbody.desc
        cps = reqbody.cps
        cc = reqbody.cc
        nameid = humanrid.generate(); key = f'class:capacity:{nameid}'
        if rdbconn.exists(key):
            response.status_code, result = 409, {'error': 'human readable id is not unique, please retry'}; return
        rdbconn.hmset(key, {'name': name, 'desc': desc, 'cps': cps, 'cc': cc})
        response.status_code, result = 200, {'nameid': nameid}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_capacity_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.put("/libresbc/class/capacity/{nameid}", status_code=200)
def update_capacity_class(reqbody: CapacityModel, nameid: str, response: Response):
    result = None
    try:
        name = reqbody.name
        desc = reqbody.desc
        cps = reqbody.cps
        cc = reqbody.cc
        key = f'class:capacity:{nameid}'
        if not rdbconn.exists(key): 
            response.status_code, result = 400, {'error': 'nonexistent class'}; return
        rdbconn.hmset(key, {'name': name, 'desc': desc, 'cps': cps, 'cc': cc})
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=update_capacity_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.delete("/libresbc/class/capacity/{nameid}", status_code=200)
def delete_capacity_class(nameid: str, response: Response):
    result = None
    try:
        if rdbconn.scard(f'engagement:capacity:{nameid}'): 
            response.status_code, result = 403, {'error': 'enageged class'}; return
        classkey = f'class:capacity:{nameid}'
        if not rdbconn.exists(classkey): 
            response.status_code, result = 400, {'error': 'nonexistent class'}; return
        rdbconn.delete(classkey)
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=delete_capacity_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libresbc/class/capacity/{nameid}", status_code=200)
def detail_capacity_class(nameid: str, response: Response):
    result = None
    try:
        classkey = f'class:capacity:{nameid}'
        if not rdbconn.exists(classkey): 
            response.status_code, result = 400, {'error': 'nonexistent class'}; return
        data = rdbconn.hgetall(classkey)
        engagements = rdbconn.smembers(f'engagement:capacity:{nameid}')
        data.update({'engagements': engagements})
        response.status_code, result = 200, data
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=detail_capacity_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libresbc/class/capacity", status_code=200)
def list_capacity_class(response: Response):
    result = None
    try:
        KEYPATTERN = f'class:capacity:*'
        next, mainkeys = rdbconn.scan(0, KEYPATTERN, SCAN_COUNT)
        while next:
            next, tmpkeys = rdbconn.scan(next, KEYPATTERN, SCAN_COUNT)
            mainkeys += tmpkeys

        for mainkey in mainkeys:
            pipe.hmget(mainkey, 'name', 'desc')
        details = pipe.execute()

        data = list()
        for mainkey, detail in zip(mainkeys, details):
            if detail:
                data.append({'nameid': mainkey.split(':')[-1], 'name': detail[0], 'desc': detail[1]})

        response.status_code, result = 200, data
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=list_capacity_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# NUMBER TRANSLATION 
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------

class TranslationModel(BaseModel):
    name: str = Field(regex=_NAME_, max_length=32, description='name of translation class')
    desc: str = Field(max_length=64, description='description')
    caller_pattern: str = Field(max_length=128, description='callerid pattern use pcre')
    callee_pattern: str = Field(max_length=128, description='callee/destination pattern use pcre')
    caller_replacement: str = Field(max_length=128, description='replacement that refer to caller_pattern use pcre')
    callee_replacement: str = Field(max_length=128, description='replacement that refer to callee_pattern use pcre')

@librerouter.post("/libresbc/class/translation", status_code=200)
def create_translation_class(reqbody: TranslationModel, response: Response):
    result = None
    try:
        name = reqbody.name
        desc = reqbody.desc
        caller_pattern = reqbody.caller_pattern
        callee_pattern = reqbody.callee_pattern
        caller_replacement = reqbody.caller_replacement
        callee_replacement = reqbody.callee_replacement
        nameid = humanrid.generate(); key = f'class:translation:{nameid}'
        if rdbconn.exists(key):
            response.status_code, result = 409, {'error': 'human readable id is not unique, please retry'}; return

        rdbconn.hmset(key, {'name': name, 'desc': desc, 'caller_pattern': caller_pattern, 'callee_pattern': callee_pattern, 
                            'caller_replacement': caller_replacement, 'callee_replacement': callee_replacement})
        response.status_code, result = 200, {'nameid': nameid}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_translation_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.put("/libresbc/class/translation/{nameid}", status_code=200)
def update_translation_class(reqbody: TranslationModel, nameid: str, response: Response):
    result = None
    try:
        name = reqbody.name
        desc = reqbody.desc
        caller_pattern = reqbody.caller_pattern
        callee_pattern = reqbody.callee_pattern
        caller_replacement = reqbody.caller_replacement
        callee_replacement = reqbody.callee_replacement
        key = f'class:translation:{nameid}'
        if not rdbconn.exists(key): 
            response.status_code, result = 400, {'error': 'nonexistent class'}; return
        rdbconn.hmset(key, {'name': name, 'desc': desc, 'caller_pattern': caller_pattern, 'callee_pattern': callee_pattern, 
                            'caller_replacement': caller_replacement, 'callee_replacement': callee_replacement})
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=update_translation_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.delete("/libresbc/class/translation/{nameid}", status_code=200)
def delete_translation_class(nameid: str, response: Response):
    result = None
    try:
        if rdbconn.scard(f'engagement:translation:{nameid}'): 
            response.status_code, result = 403, {'error': 'enageged class'}; return
        classkey = f'class:translation:{nameid}'
        if not rdbconn.exists(classkey): 
            response.status_code, result = 400, {'error': 'nonexistent class'}; return
        rdbconn.delete(classkey)
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=delete_translation_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libresbc/class/translation/{nameid}", status_code=200)
def detail_translation_class(nameid: str, response: Response):
    result = None
    try:
        classkey = f'class:translation:{nameid}'
        if not rdbconn.exists(classkey): 
            response.status_code, result = 400, {'error': 'nonexistent class'}; return
        data = rdbconn.hgetall(classkey)
        engagements = rdbconn.smembers(f'engagement:translation:{nameid}')
        data.update({'engagements': engagements})
        response.status_code, result = 200, data
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=detail_translation_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libresbc/class/translation", status_code=200)
def list_translation_class(response: Response):
    result = None
    try:
        KEYPATTERN = f'class:translation:*'
        next, mainkeys = rdbconn.scan(0, KEYPATTERN, SCAN_COUNT)
        while next:
            next, tmpkeys = rdbconn.scan(next, KEYPATTERN, SCAN_COUNT)
            mainkeys += tmpkeys

        for mainkey in mainkeys:
            pipe.hmget(mainkey, 'name', 'desc')
        details = pipe.execute()

        data = list()
        for mainkey, detail in zip(mainkeys, details):
            if detail:
                data.append({'nameid': mainkey.split(':')[-1], 'name': detail[0], 'desc': detail[1]})

        response.status_code, result = 200, data
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=list_translation_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# INBOUND INTERCONECTION
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------

class ClassModel(BaseModel):
    codec: str = Field(description='nameid of codec class')
    capacity: str = Field(description='nameid of capacity class')
    translations: List[str] = Field(default=[], min_items=0, max_item=5, description='a set of translation class')
    manipulations: List[str] = Field(default=[], min_items=0, max_item=5, description='a set of manipulations class')

    @validator('codec', pre=True)
    def check_codec_existent(cls, nameid):
        if not rdbconn.exists(f'class:codec:{nameid}'):
            raise ValueError('nonexistent class')
        return nameid

    @validator('capacity', pre=True)
    def check_capacity_existent(cls, nameid):
        if not rdbconn.exists(f'class:capacity:{nameid}'):
            raise ValueError('nonexistent class')
        return nameid

    @validator('manipulations', pre=True)
    def check_manipulation_existent(cls, nameids):
        for nameid in nameids:
            if not rdbconn.exists(f'class:manipulation:{nameid}'):
                raise ValueError('nonexistent class')
            return nameid

    @validator('translations', pre=True)
    def check_translation_existent(cls, nameids):
        for nameid in nameids:
            if not rdbconn.exists(f'class:translation:{nameid}'):
                raise ValueError('nonexistent class')
            return nameids

class InboundInterconnection(BaseModel):
    name: str = Field(regex=_NAME_, max_length=32, description='name of inbound interconnection')
    desc: str = Field(max_length=64, description='description')
    sipprofile: str = Field(description='a sip profile nameid that interconnection engage to')
    accesses: List[IPv4Address] = Field(min_items=1, max_item=10, description='a set of signalling that use for SIP')
    medias: List[IPv4Network] = Field(min_items=1, max_item=20, description='a set of IPv4 Network that use for RTP')
    classes: ClassModel = Field(description='an object of class include codec, capacity, translations, manipulations')
    nodes: List[str] = Field(default=['_ALL_'], min_items=1, max_item=len(CLUSTERMEMBERS), description='a set of node member that interconnection engage to')
    enable: bool = Field(default=True, description='enable/disable this interconnection')


    @validator('sipprofile', pre=True)
    def check_sipprofile(cls, nameid):
        if not rdbconn.exists(f'sipprofile:{nameid}'):
            raise ValueError('nonexistent sipprofile')
        return nameid

    @validator('nodes', pre=True)
    def check_node(cls, nodes):
        for node in nodes:
            if node != '_ALL_' and node not in CLUSTERMEMBERS:
                raise ValueError('nonexistent node')
        return nodes


@librerouter.post("/libresbc/interconnection/inbound", status_code=200)
def create_inbound_interconnection(reqbody: InboundInterconnection, response: Response):
    result = None
    try:
        name = reqbody.name
        desc = reqbody.desc
        sipprofile = reqbody.sipprofile
        accesses = reqbody.accesses
        medias = reqbody.medias
        codec = reqbody.classes.codec
        capacity = reqbody.classes.capacity
        translations = reqbody.classes.translations
        manipulations = reqbody.classes.manipulations
        nodes = reqbody.nodes
        enable = reqbody.enable
        # standardize data form
        accesses = set(map(str, accesses))
        medias = set(map(str, medias))
        nodes = set(map(str, medias))
        nameid = humanrid.generate()
        if rdbconn.exists(f'interconnection:{nameid}:attribute'):
            response.status_code, result = 409, {'error': 'human readable id is not unique, please retry'}; return

        for access in accesses:
            if rdbconn.exists(f'recognition:{sipprofile}:{str(access)}'):
                response.status_code, result = 403, {'error': 'nonunique_ip_access'}; return

        pipe.hmset(f'interconnection:{nameid}:attribute', {'name': name, 'desc': desc, 'direction': 'inbound', 'sipprofile': sipprofile, nodes: json.dumps(nodes), 'enable': bool2int(enable)})
        for node in nodes: pipe.sadd(f'engagement:node:{node}', nameid)
        pipe.sadd(f'engagement:sipprofile:{sipprofile}', nameid)

        pipe.hmset(f'interconnection:{nameid}:classes', {'codec': codec, 'capacity': capacity, 'translations': json.dumps(translations), 'manipulations': json.dumps(manipulations)})
        pipe.sadd(f'engagement:codec:{codec}', nameid)
        pipe.sadd(f'engagement:capacity:{capacity}', nameid)
        for translation in translations: pipe.sadd(f'engagement:translation:{translation}', nameid)
        for manipulation in manipulations: pipe.sadd(f'engagement:manipulation:{manipulation}', nameid)

        for access in accesses:
            ip = str(access)
            pipe.sadd(f'interconnection:{nameid}:accesses', ip)
            pipe.set(f'recognition:{sipprofile}:{ip}', nameid)
        for media in medias:
            pipe.sadd(f'interconnection:{nameid}:medias', str(media))
        pipe.execute()
        response.status_code, result = 200, {'nameid': nameid}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_inbound_interconnection, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.delete("/libresbc/interconnection/inbound/{nameid}", status_code=200)
def delete_inbound_interconnection(nameid: str, response: Response):
    result = None
    try:
        if not rdbconn.exists(f'interconnection:{nameid}:attribute'):
            response.status_code, result = 403, {'error': 'nonexistent interconnection'}; return

        sipprofile = rdbconn.hget(f'interconnection:{nameid}:attribute', 'sipprofile')
        pipe.srem(f'engagement:sipprofile:{sipprofile}', nameid)
        nodes = json.loads(rdbconn.hget(f'interconnection:{nameid}:attribute', 'nodes'))
        for node in nodes: pipe.srem(f'engagement:node:{node}', nameid)
        pipe.delete(f'interconnection:{nameid}:attribute')

        codec = rdbconn.hset(f'interconnection:{nameid}:classes', 'codec')
        pipe.srem(f'engagement:codec:{codec}', nameid)
        capacity = rdbconn.hset(f'interconnection:{nameid}:classes', 'capacity')
        pipe.srem(f'engagement:capacity:{capacity}', nameid)
        translations = json.loads(rdbconn.hget(f'interconnection:{nameid}:classes', 'translations'))
        for translation in translations: pipe.srem(f'engagement:translation:{translation}', nameid)
        manipulations = json.loads(rdbconn.hget(f'interconnection:{nameid}:classes', 'manipulations'))
        for manipulation in manipulations: pipe.srem(f'engagement:manipulation:{manipulation}', nameid)
        pipe.delete(f'interconnection:{nameid}:classes')

        accesses = rdbconn.smembers(f'interconnection:{nameid}:accesses')
        for access in accesses:
            ip = str(access)
            pipe.delete(f'recognition:{sipprofile}:{ip}')
            pipe.srem(f'interconnection:{nameid}:accesses', ip)
        pipe.delete(f'interconnection:{nameid}:medias')
        pipe.execute()

        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=delete_inbound_interconnection, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.put("/libresbc/interconnection/inbound/{nameid}", status_code=200)
def update_inbound_interconnection(reqbody: InboundInterconnection, nameid: str, response: Response):
    result = None
    try:
        name = reqbody.name
        desc = reqbody.desc
        sipprofile = reqbody.sipprofile
        accesses = reqbody.accesses
        medias = reqbody.medias
        codec = reqbody.classes.codec
        capacity = reqbody.classes.capacity
        translations = reqbody.classes.translations
        manipulations = reqbody.classes.manipulations
        nodes = reqbody.nodes
        enable = reqbody.enable
        # standardize data form
        accesses = set(map(str, accesses))
        medias = set(map(str, medias))
        nodes = set(map(str, medias))

        if not rdbconn.exists(f'interconnection:{nameid}:attribute'):
            response.status_code, result = 400, {'error': 'nonexistent interconnection'}; return

        for access in accesses:
            tmpnameid = rdbconn.exists(f'recognition:{sipprofile}:{str(access)}')
            if tmpnameid and tmpnameid!=nameid:
                response.status_code, result = 403, {'error': 'nonunique_ip_access'}; return

        _sipprofile = rdbconn.hget(f'interconnection:{nameid}:attribute', 'sipprofile')
        pipe.srem(f'engagement:sipprofile:{_sipprofile}', nameid)
        pipe.sadd(f'engagement:sipprofile:{sipprofile}', nameid)
        _nodes = set(json.loads(rdbconn.hget(f'interconnection:{nameid}:attribute', 'nodes')))
        for node in _nodes-nodes: pipe.srem(f'engagement:node:{node}', nameid)
        for node in nodes-_nodes: pipe.sadd(f'engagement:node:{node}', nameid)

        pipe.hmset(f'interconnection:{nameid}:attribute', {'name': name, 'desc': desc, 'sipprofile': sipprofile, nodes: json.dumps(nodes), 'enable': bool2int(enable)})

        codec = rdbconn.hset(f'interconnection:{nameid}:classes', 'codec')
        pipe.srem(f'engagement:codec:{codec}', nameid)
        capacity = rdbconn.hset(f'interconnection:{nameid}:classes', 'capacity')
        pipe.srem(f'engagement:capacity:{capacity}', nameid)
        translations = json.loads(rdbconn.hget(f'interconnection:{nameid}:classes', 'translations'))
        for translation in translations: pipe.srem(f'engagement:translation:{translation}', nameid)
        manipulations = json.loads(rdbconn.hget(f'interconnection:{nameid}:classes', 'manipulations'))
        for manipulation in manipulations: pipe.srem(f'engagement:manipulation:{manipulation}', nameid)
        pipe.hmset(f'interconnection:{nameid}:classes', {'codec': codec, 'capacity': capacity, 'translations': json.dumps(translations), 'manipulations': json.dumps(manipulations)})
        pipe.sadd(f'engagement:codec:{codec}', nameid)
        pipe.sadd(f'engagement:capacity:{capacity}', nameid)
        for translation in translations: pipe.sadd(f'engagement:translation:{translation}', nameid)
        for manipulation in manipulations: pipe.sadd(f'engagement:manipulation:{manipulation}', nameid)

        _accesses = set(rdbconn.smembers(f'interconnection:{nameid}:accesses'))
        for ip in _accesses -  accesses:
            pipe.delete(f'recognition:{sipprofile}:{ip}')
            pipe.srem(f'interconnection:{nameid}:accesses', ip)
        for ip in accesses - _accesses:
            pipe.sadd(f'interconnection:{nameid}:accesses', ip)
            pipe.set(f'recognition:{sipprofile}:{ip}', nameid)
        pipe.delete(f'interconnection:{nameid}:medias')
        for media in medias:
            pipe.sadd(f'interconnection:{nameid}:medias', str(media))
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=update_inbound_interconnection, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libresbc/interconnection/inbound/{nameid}", status_code=200)
def detail_inbound_interconnection(nameid: str, response: Response):
    result = None
    try:
        if not rdbconn.exists(f'interconnection:{nameid}:attribute'):
            response.status_code, result = 400, {'error': 'nonexistent interconnection'}; return
        interconnection = rdbconn.hgetall(f'interconnection:{nameid}:attribute')
        interconnection['nodes'] = json.loads(interconnection['nodes'])
        interconnection['enable'] = int2bool(interconnection['enable'])
        classes = rdbconn.hgetall(f'interconnection:{nameid}:classes')
        classes['translations'] = json.loads(classes['translations'])
        classes['manipulations'] = json.loads(classes['manipulations'])
        medias = rdbconn.smembers(f'interconnection:{nameid}:medias')
        accesses = rdbconn.smembers(f'interconnection:{nameid}:accesses')
        engagements = rdbconn.smembers(f'engagement:interconnection:{nameid}')
        interconnection.update({'accesses': accesses, 'classes': classes, 'medias': medias, 'engagements': engagements})
        response.status_code, result = 200, interconnection
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=detail_inbound_interconnection, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# OUTBOUND INTERCONECTION
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
class TransportEnum(str, Enum):
    UDP = "UDP"
    TCP = "TCP"
    TLS = "TLS"

class DistributionEnum(str, Enum):
    round_robin = 'round_robin'
    hash_caller = 'hash_caller'
    hash_callee = 'hash_callee'
    hash_both = 'hash_both'
    weight_based = 'weight_based'

class GatewayModel(BaseModel):
    ip: IPv4Address = Field(description='farend ip address')
    port: int = Field(ge=0, le=65535, description='farend destination port')
    transport: TransportEnum = Field(default=TransportEnum.UDP, description='farend transport protocol')
    weight: int = Field(default=1, ge=0, le=99, description='weight based load distribution')
    username: str = Field(default='', description='digest auth username')
    password: str = Field(default='', description='digest auth password')
    realm: str = Field(default='', description='digest auth realm')
    reigister: bool = Field(default=False, description='register')
    register_proxy: str = Field(default='', description='proxy address to register')
    sip_cid_type: str = Field(default='none', description='caller id type: rpid, pid, none')
    caller_id_in_from: bool = Field(default=False, description='caller id in from hearder')
    ping: int = Field(default=0, ge=5, le=3600, description='the period (second) to send SIP OPTION')
    ping_max: int = Field(default=1, ge=1, le=31, description='number of success pings to declaring a gateway up')
    ping_min: int = Field(default=1, ge=1, le=31,description='number of failure pings to declaring a gateway down')
    privacy: str = Field(default='no', description='caller privacy on calls')

class OutboundInterconnection(BaseModel):
    name: str = Field(regex=_NAME_, max_length=32, description='name of outbound interconnection')
    desc: str = Field(max_length=64, description='description')
    sipprofile: str = Field(description='a sip profile nameid that interconnection engage to')
    distribution: DistributionEnum = Field(default=DistributionEnum.round_robin, description='The method selects a destination from addresses set')
    gateways: List[GatewayModel] = Field(min_items=1, max_item=20, description='list of outbound gateways')
    medias: List[IPv4Network] = Field(min_items=1, max_item=20, description='a set of IPv4 Network that use for RTP')
    clases: ClassModel = Field(description='an object of class include codec, capacity, translations, manipulations')
    nodes: List[str] = Field(default=['_ALL_'], min_items=1, max_item=len(CLUSTERMEMBERS), description='a set of node member that interconnection engage to')
    enable: bool = Field(default=True, description='enable/disable this interconnection')

    @validator('sipprofile', pre=True)
    def check_sipprofile(cls, nameid):
        if not rdbconn.exists(f'sipprofile:{nameid}'):
            raise ValueError('nonexistent sipprofile')
        return nameid

@librerouter.post("/libresbc/interconnection/outbound", status_code=200)
def create_outbound_interconnection(reqbody: OutboundInterconnection, response: Response):
    result = None
    try:
        name = reqbody.name
        desc = reqbody.desc
        sipprofile = reqbody.sipprofile
        distribution = reqbody.distribution.name
        gateways = reqbody.gateways
        medias = reqbody.medias
        codec = reqbody.classes.codec
        capacity = reqbody.classes.capacity
        translations = reqbody.classes.translations
        manipulations = reqbody.classes.manipulations
        nodes = reqbody.nodes
        enable = reqbody.enable
        # standardize data form
        medias = set(map(str, medias))
        nodes = set(map(str, nodes))
        nameid = humanrid.generate()
        if rdbconn.exists(f'interconnection:{nameid}:attribute'):
            response.status_code, result = 409, {'error': 'human readable id is not unique, please retry'}; return

        pipe.hmset(f'interconnection:{nameid}:attribute', {'name': name, 'desc': desc, 'direction': 'outbound', 'sipprofile': sipprofile, 'distribution': distribution, nodes: json.dumps(nodes), 'enable': bool2int(enable)})
        for node in nodes: pipe.sadd(f'engagement:node:{node}', nameid)
        pipe.sadd(f'engagement:sipprofile:{sipprofile}', nameid)
        pipe.hmset(f'interconnection:{nameid}:classes', {'codec': codec, 'capacity': capacity, 'translations': json.dumps(translations), 'manipulations': json.dumps(manipulations)})
        pipe.sadd(f'engagement:codec:{codec}', nameid)
        pipe.sadd(f'engagement:capacity:{capacity}', nameid)
        for translation in translations: pipe.sadd(f'engagement:translation:{translation}', nameid)
        for manipulation in manipulations: pipe.sadd(f'engagement:manipulation:{manipulation}', nameid)

        pipe.set(f'interconnection:{nameid}:gateways', json.dumps(gateways.dict()))
        for media in medias:
            pipe.sadd(f'interconnection:{nameid}:medias', str(media))
        pipe.execute()
        response.status_code, result = 200, {'nameid': nameid}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_outbound_interconnection, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


@librerouter.post("/libresbc/interconnection/outbound/{nameid}", status_code=200)
def update_outbound_interconnection(reqbody: OutboundInterconnection, nameid: str, response: Response):
    result = None
    try:
        name = reqbody.name
        desc = reqbody.desc
        sipprofile = reqbody.sipprofile
        distribution = reqbody.distribution.name
        gateways = reqbody.gateways
        medias = reqbody.medias
        codec = reqbody.classes.codec
        capacity = reqbody.classes.capacity
        translations = reqbody.classes.translations
        manipulations = reqbody.classes.manipulations
        nodes = reqbody.nodes
        enable = reqbody.enable
        # standardize data form
        medias = set(map(str, medias))
        nodes = set(map(str, nodes))

        if rdbconn.exists(f'interconnection:{nameid}:attribute'):
            response.status_code, result = 400, {'error': 'nonexistent interconnection'}; return

        _sipprofile = rdbconn.hget(f'interconnection:{nameid}:attribute', 'sipprofile')
        pipe.srem(f'engagement:sipprofile:{_sipprofile}', nameid)
        pipe.sadd(f'engagement:sipprofile:{sipprofile}', nameid)
        _nodes = set(json.loads(rdbconn.hget(f'interconnection:{nameid}:attribute', 'nodes')))
        for node in _nodes-nodes: pipe.srem(f'engagement:node:{node}', nameid)
        for node in nodes-_nodes:pipe.sadd(f'engagement:node:{node}', nameid)
        pipe.hmset(f'interconnection:{nameid}:attribute', {'name': name, 'desc': desc, 'sipprofile': sipprofile, 'distribution': distribution, nodes: json.dumps(nodes), 'enable': bool2int(enable)})

        codec = rdbconn.hset(f'interconnection:{nameid}:classes', 'codec')
        pipe.srem(f'engagement:codec:{codec}', nameid)
        capacity = rdbconn.hset(f'interconnection:{nameid}:classes', 'capacity')
        pipe.srem(f'engagement:capacity:{capacity}', nameid)
        translations = json.loads(rdbconn.hget(f'interconnection:{nameid}:classes', 'translations'))
        for translation in translations: pipe.srem(f'engagement:translation:{translation}', nameid)
        manipulations = json.loads(rdbconn.hget(f'interconnection:{nameid}:classes', 'manipulations'))
        for manipulation in manipulations: pipe.srem(f'engagement:manipulation:{manipulation}', nameid)
        pipe.hmset(f'interconnection:{nameid}:classes', {'codec': codec, 'capacity': capacity, 'translations': json.dumps(translations), 'manipulations': json.dumps(manipulations)})
        pipe.sadd(f'engagement:codec:{codec}', nameid)
        pipe.sadd(f'engagement:capacity:{capacity}', nameid)
        for translation in translations: pipe.sadd(f'engagement:translation:{translation}', nameid)
        for manipulation in manipulations: pipe.sadd(f'engagement:manipulation:{manipulation}', nameid)

        pipe.set(f'interconnection:{nameid}:gateways', json.dumps(gateways.dict()))
        pipe.delete(f'interconnection:{nameid}:medias')
        for media in medias:
            pipe.sadd(f'interconnection:{nameid}:medias', str(media))
        pipe.execute()
        #
        response.status_code, result = 200, {'nameid': nameid}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=update_outbound_interconnection, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.delete("/libresbc/interconnection/outbound/{nameid}", status_code=200)
def delete_outbound_interconnection(nameid: str, response: Response):
    result = None
    try:
        if not rdbconn.exists(f'interconnection:{nameid}:attribute'):
            response.status_code, result = 403, {'error': 'nonexistent interconnection'}; return

        sipprofile = rdbconn.hget(f'interconnection:{nameid}:attribute', 'sipprofile')
        pipe.srem(f'engagement:sipprofile:{sipprofile}', nameid)
        nodes = json.loads(rdbconn.hget(f'interconnection:{nameid}:attribute', 'nodes'))
        for node in nodes: pipe.srem(f'engagement:node:{node}', nameid)
        pipe.delete(f'interconnection:{nameid}:attribute')

        codec = rdbconn.hset(f'interconnection:{nameid}:classes', 'codec')
        pipe.srem(f'engagement:codec:{codec}', nameid)
        capacity = rdbconn.hset(f'interconnection:{nameid}:classes', 'capacity')
        pipe.srem(f'engagement:capacity:{capacity}', nameid)
        translations = json.loads(rdbconn.hget(f'interconnection:{nameid}:classes', 'translations'))
        for translation in translations: pipe.srem(f'engagement:translation:{translation}', nameid)
        manipulations = json.loads(rdbconn.hget(f'interconnection:{nameid}:classes', 'manipulations'))
        for manipulation in manipulations: pipe.srem(f'engagement:manipulation:{manipulation}', nameid)
        pipe.delete(f'interconnection:{nameid}:classes')

        pipe.delete(f'interconnection:{nameid}:gateways')
        pipe.delete(f'interconnection:{nameid}:medias')
        pipe.execute()

        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=delete_outbound_interconnection, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libresbc/interconnection/outbound/{nameid}", status_code=200)
def detail_outbound_interconnection(nameid: str, response: Response):
    result = None
    try:
        if not rdbconn.exists(f'interconnection:{nameid}:attribute'):
            response.status_code, result = 400, {'error': 'nonexistent interconnection'}; return
        interconnection = rdbconn.hgetall(f'interconnection:{nameid}:attribute')
        interconnection['nodes'] = json.loads(interconnection['nodes'])
        interconnection['enable'] = int2bool(interconnection['enable'])
        classes = rdbconn.hgetall(f'interconnection:{nameid}:classes')
        classes['translations'] = json.loads(classes['translations'])
        classes['manipulations'] = json.loads(classes['manipulations'])
        medias = rdbconn.smembers(f'interconnection:{nameid}:medias')
        gateways = json.loads(rdbconn.smembers(f'interconnection:{nameid}:gateways'))
        engagements = rdbconn.smembers(f'engagement:interconnection:{nameid}')
        interconnection.update({'gateways': gateways, 'classes': classes, 'medias': medias, 'engagements': engagements})
        response.status_code, result = 200, interconnection
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=detail_outbound_interconnection, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
@librerouter.get("/libresbc/interconnection", status_code=200)
def list_interconnect(response: Response):
    result = None
    try:
        KEYPATTERN = 'interconnection:*:attribute'
        next, mainkeys = rdbconn.scan(0, KEYPATTERN, SCAN_COUNT)
        while next:
            next, tmpkeys = rdbconn.scan(next, KEYPATTERN, SCAN_COUNT)
            mainkeys += tmpkeys

        for mainkey in mainkeys:
            pipe.hmget(mainkey, 'name', 'desc', 'sipprofile', 'direction')
        details = pipe.execute()

        data = list()
        for mainkey, detail in zip(mainkeys, details):
            data.append({'nameid': mainkey.split(':')[-1], 'name': detail[0], 'desc': detail[1], 'sipprofile': detail[2], 'direction': detail[3]})

        response.status_code, result = 200, data
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=list_interconnect, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result