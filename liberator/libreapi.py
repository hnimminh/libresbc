import traceback
import re
import json

import redis
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from enum import Enum
from ipaddress import IPv4Address, IPv4Network
from fastapi import APIRouter, Request, Response, Path
from fastapi.encoders import jsonable_encoder

from configuration import (_APPLICATION, _SWVERSION, _DESCRIPTION, 
                           NODEID, CLUSTERNAME, CLUSTERMEMBERS,
                           SWCODECS, MAX_CPS, MAX_ACTIVE_SESSION, 
                           REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD, SCAN_COUNT)
from utilities import logify, debugy, get_request_uuid, int2bool, bool2int, humanrid, redishash, jsonhash


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
    _clustername = rdbconn.get('cluster:name')
    if _clustername: CLUSTERNAME = _clustername
    _clustermembers = set(rdbconn.smembers('cluster:members')) 
    if _clustermembers: CLUSTERMEMBERS = _clustermembers
except:
    pass

def listify(string, delimiter=':') -> list:
    assert isinstance(string, str)
    return string.split(delimiter)

def getnameid(string) -> str:
    return string.split(':')

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# PREDEFINED INFORMATION
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
@librerouter.get("/libresbc/predefine", status_code=200)
def predefine():
    return {
        "nodeid": NODEID,
        "cluster": {
            "name": CLUSTERNAME,
            "members": CLUSTERMEMBERS
        },
        "application": _APPLICATION,
        'swversion': _SWVERSION,
        "description": _DESCRIPTION
    }

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# CLUSTER & NODE
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
class ClusterModel(BaseModel):
    name: str = Field(regex=_NAME_, max_length=32, description='The name of libresbc cluster')
    members: List[str] = Field(min_items=1, max_item=16, description='The member of libresbc cluster')


@librerouter.put("/libresbc/cluster", status_code=200)
def update_cluster(reqbody: ClusterModel, response: Response):
    result = None
    try:
        name = reqbody.name
        members = set(reqbody.members)
        _members = set(rdbconn.smembers('cluster:members'))
  
        removed_members = _members - members
        for removed_member in removed_members:
            if rdbconn.scard(f'engagement:node:{removed_member}'):
                response.status_code, result = 403, {'error': 'engaged node'}; return

        pipe.set('cluster:name', name)
        for member in members: pipe.sadd('cluster:members', member)
        pipe.execute()
        CLUSTERNAME, CLUSTERMEMBERS = name, members
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
        response.status_code, result = 200, {'name': CLUSTERNAME, 'members': CLUSTERMEMBERS}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=get_cluster, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# SIP PROFILES 
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
class SIPProfileModel(BaseModel):
    name: str = Field(regex=_NAME_, max_length=32, description='friendly name of sip profile')
    desc: Optional[str] = Field(default='', max_length=64, description='description')
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
    tls_version: str = Field(default='tlsv1.2', description='TLS version')
    tls_cert_dir: str = Field(default='', description='TLS Certificate dirrectory')


@librerouter.post("/libresbc/sipprofile", status_code=200)
def create_sipprofile(reqbody: SIPProfileModel, response: Response):
    result = None
    try:
        name = reqbody.name
        data = jsonable_encoder(reqbody)
        name_key = f'sipprofile:{name}'
        if rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent sip profile name'}; return
        rdbconn.hmset(name_key, redishash(data))
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_sipprofile, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.put("/libresbc/sipprofile/{identifier}", status_code=200)
def update_sipprofile(reqbody: SIPProfileModel, identifier: str, response: Response):
    result = None
    try:
        name = reqbody.name
        data = jsonable_encoder(reqbody)
        _name_key = f'sipprofile:{identifier}'
        _engaged_key = f'engagement:{_name_key}'
        name_key = f'sipprofile:{name}'
        engaged_key = f'engagement:{name_key}'
        if not rdbconn.exists(_name_key): 
            response.status_code, result = 403, {'error': 'nonexistent sip profile identifier'}; return
        if name != identifier and rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent sip profile name'}; return
        rdbconn.hmset(name_key, redishash(data))
        if name != identifier:
            engagements = rdbconn.smembers(_engaged_key)
            for engagement in engagements:
                pipe.hset(engagement, name)
            if rdbconn.exists(_engaged_key):
                pipe.rename(_engaged_key, engaged_key)
            pipe.delete(_name_key)
            pipe.execute()
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=update_sipprofile, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.delete("/libresbc/sipprofile/{identifier}", status_code=200)
def delete_sipprofile(identifier: str, response: Response):
    result = None
    try:
        _name_key = f'sipprofile:{identifier}'
        _engage_key = f'engagement:{_name_key}'
        if rdbconn.scard(_engage_key): 
            response.status_code, result = 403, {'error': 'engaged sipprofile'}; return
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent sipprofile'}; return
        pipe.delete(_engage_key)
        pipe.delete(_name_key)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=delete_sipprofile, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libresbc/sipprofile/{identifier}", status_code=200)
def detail_sipprofile(identifier: str, response: Response):
    result = None
    try:
        _name_key = f'sipprofile:{identifier}'
        _engage_key = f'engagement:{_name_key}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent sip profile'}; return
        result = jsonhash(rdbconn.hgetall(_name_key))
        engagements = rdbconn.smembers(_engage_key)
        result.update({'engagements': engagements})
        response.status_code = 200
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
            pipe.hmget(mainkey, 'desc')
        details = pipe.execute()

        data = list()
        for mainkey, detail in zip(mainkeys, details):
            if detail:
                data.append({'name': getnameid(mainkey), 'desc': detail[0]})

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
    name: str = Field(regex=_NAME_, max_length=32, description='name of codec class (identifier)')
    desc: Optional[str] = Field(default='', max_length=64, description='description')
    codecs: List[CodecEnum] = Field(min_items=1, max_item=len(SWCODECS), description='sorted list of codec')


@librerouter.post("/libresbc/class/codec", status_code=200)
def create_codec_class(reqbody: CodecModel, response: Response):
    result = None
    try:
        name = reqbody.name
        data = jsonable_encoder(reqbody)
        name_key = f'class:codec:{name}'
        if rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent class name'}; return
        rdbconn.hmset(name_key, redishash(data))
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_codec_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.put("/libresbc/class/codec/{identifier}", status_code=200)
def update_codec_class(reqbody: CodecModel, identifier: str, response: Response):
    result = None
    try:
        name = reqbody.name
        data = jsonable_encoder(reqbody)
        _name_key = f'class:codec:{identifier}'
        _engaged_key = f'engagement:{_name_key}'
        name_key = f'class:codec:{name}'
        engaged_key = f'engagement:{name_key}'
        if not rdbconn.exists(_name_key): 
            response.status_code, result = 403, {'error': 'nonexistent class identifier'}; return
        if name != identifier and rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent class name'}; return
        rdbconn.hmset(name_key, redishash(data))
        if name != identifier:
            engagements = rdbconn.smembers(_engaged_key)
            for engagement in engagements:
                pipe.hset(engagement, name)
            if rdbconn.exists(_engaged_key):
                pipe.rename(_engaged_key, engaged_key)
            pipe.delete(_name_key)
            pipe.execute()
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=update_codec_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.delete("/libresbc/class/codec/{identifier}", status_code=200)
def delete_codec_class(identifier: str, response: Response):
    result = None
    try:
        _name_key = f'class:codec:{identifier}'
        _engage_key = f'engagement:{_name_key}'
        if rdbconn.scard(_engage_key): 
            response.status_code, result = 403, {'error': 'engaged class'}; return
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent class identifier'}; return
        pipe.delete(_engage_key)
        pipe.delete(_name_key)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=delete_codec_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libresbc/class/codec/{identifier}", status_code=200)
def detail_codec_class(identifier: str, response: Response):
    result = None
    try:
        _name_key = f'class:codec:{identifier}'
        _engage_key = f'engagement:{_name_key}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent class identifier'}; return
        result = jsonhash(rdbconn.hgetall(_name_key))
        engagements = rdbconn.smembers(_engage_key)
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
            pipe.hmget(mainkey, 'desc')
        details = pipe.execute()

        data = list()
        for mainkey, detail in zip(mainkeys, details):
            if detail:
                data.append({'name': getnameid(mainkey), 'desc': detail[0]})

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
    name: str = Field(regex=_NAME_, max_length=32, description='name of capacity class (identifier)')
    desc: Optional[str] = Field(default='', max_length=64, description='description')
    cps: int = Field(default=2, ge=1, le=len(CLUSTERMEMBERS)*MAX_CPS//2, description='call per second')
    ccs: int = Field(default=10, ge=1, le=len(CLUSTERMEMBERS)*MAX_ACTIVE_SESSION//2, description='concurrent calls')


@librerouter.post("/libresbc/class/capacity", status_code=200)
def create_capacity_class(reqbody: CapacityModel, response: Response):
    result = None
    try:
        name = reqbody.name
        data = jsonable_encoder(reqbody)
        name_key = f'class:capacity:{name}'
        if rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent class name'}; return
        rdbconn.hmset(name_key, redishash(data))
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_capacity_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.put("/libresbc/class/capacity/{identifier}", status_code=200)
def update_capacity_class(reqbody: CapacityModel, identifier: str, response: Response):
    result = None
    try:
        name = reqbody.name
        data = jsonable_encoder(reqbody)
        _name_key = f'class:capacity:{identifier}'
        _engaged_key = f'engagement:{_name_key}'
        name_key = f'class:capacity:{name}'
        engaged_key = f'engagement:{name_key}'
        if not rdbconn.exists(_name_key): 
            response.status_code, result = 403, {'error': 'nonexistent class identifier'}; return
        if name != identifier and rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent class name'}; return
        rdbconn.hmset(name_key, redishash(data))
        if name != identifier:
            engagements = rdbconn.smembers(_engaged_key)
            for engagement in engagements:
                pipe.hset(engagement, name)
            if rdbconn.exists(_engaged_key):
                pipe.rename(_engaged_key, engaged_key)
            pipe.delete(_name_key)
            pipe.execute()
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=update_capacity_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.delete("/libresbc/class/capacity/{identifier}", status_code=200)
def delete_capacity_class(identifier: str, response: Response):
    result = None
    try:
        _name_key = f'class:capacity:{identifier}'
        _engaged_key = f'engagement:{_name_key}'
        if rdbconn.scard(_engaged_key): 
            response.status_code, result = 403, {'error': 'engaged class'}; return
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent class identifier'}; return
        pipe.delete(_engaged_key)
        pipe.delete(_name_key)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=delete_capacity_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libresbc/class/capacity/{identifier}", status_code=200)
def detail_capacity_class(identifier: str, response: Response):
    result = None
    try:
        _name_key = f'class:capacity:{identifier}'
        _engaged_key = f'engagement:{_name_key}'
        if not rdbconn.exists(_name_key): 
            response.status_code, result = 403, {'error': 'nonexistent class identifier'}; return
        result = jsonhash(rdbconn.hgetall(_name_key))
        engagements = rdbconn.smembers(_engaged_key)
        result.update({'engagements': engagements})
        response.status_code = 200
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
            pipe.hmget(mainkey, 'desc')
        details = pipe.execute()

        data = list()
        for mainkey, detail in zip(mainkeys, details):
            if detail:
                data.append({'name': getnameid(mainkey), 'desc': detail[0]})

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
    desc: Optional[str] = Field(default='', max_length=64, description='description')
    caller_pattern: str = Field(max_length=128, description='caller pattern use pcre')
    callee_pattern: str = Field(max_length=128, description='callee pattern use pcre')
    caller_replacement: str = Field(max_length=128, description='replacement that refer to caller pattern use pcre')
    callee_replacement: str = Field(max_length=128, description='replacement that refer to callee pattern use pcre')

@librerouter.post("/libresbc/class/translation", status_code=200)
def create_translation_class(reqbody: TranslationModel, response: Response):
    result = None
    try:
        name = reqbody.name
        data = jsonable_encoder(reqbody)
        name_key = f'class:translation:{name}'
        if rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent class name'}; return
        rdbconn.hmset(name_key, data)
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_translation_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.put("/libresbc/class/translation/{identifier}", status_code=200)
def update_translation_class(reqbody: TranslationModel, identifier: str, response: Response):
    result = None
    try:
        name = reqbody.name
        data = jsonable_encoder(reqbody)
        _name_key = f'class:translation:{identifier}'
        _engaged_key = f'engagement:{_name_key}'
        name_key = f'class:translation:{name}'
        engaged_key = f'engagement:{name_key}'
        if not rdbconn.exists(_name_key): 
            response.status_code, result = 403, {'error': 'nonexistent class identifier'}; return
        if name != identifier and rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent class name'}; return
        rdbconn.hmset(name_key, data)
        if name != identifier:
            engagements = rdbconn.smembers(_engaged_key)
            for engagement in engagements:
                pipe.hset(engagement, name)
            if rdbconn.exists(_engaged_key):
                pipe.rename(_engaged_key, engaged_key)
            pipe.delete(_name_key)
            pipe.execute()
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=update_translation_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.delete("/libresbc/class/translation/{identifier}", status_code=200)
def delete_translation_class(identifier: str, response: Response):
    result = None
    try:
        _name_key = f'class:translation:{identifier}'
        _engaged_key = f'engagement:{_name_key}'
        if rdbconn.scard(_engaged_key): 
            response.status_code, result = 403, {'error': 'engaged class'}; return
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent class identifier'}; return
        pipe.delete(_engaged_key)
        pipe.delete(_name_key)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=delete_translation_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libresbc/class/translation/{identifier}", status_code=200)
def detail_translation_class(identifier: str, response: Response):
    result = None
    try:
        _name_key = f'class:translation:{identifier}'
        _engaged_key = f'engagement:{_name_key}'
        if not rdbconn.exists(_name_key): 
            response.status_code, result = 403, {'error': 'nonexistent class identifier'}; return
        result = rdbconn.hgetall(_name_key)
        engagements = rdbconn.smembers(_engaged_key)
        result.update({'engagements': engagements})
        response.status_code = 200
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
            pipe.hmget(mainkey, 'desc')
        details = pipe.execute()

        data = list()
        for mainkey, detail in zip(mainkeys, details):
            if detail:
                data.append({'name': getnameid(mainkey), 'desc': detail[0]})
        response.status_code, result = 200, data
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=list_translation_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------

def check_existent_codec(nameid):
    if not rdbconn.exists(f'class:codec:{nameid}'):
        raise ValueError('nonexistent class')
    return nameid

def check_existent_capacity(nameid):
    if not rdbconn.exists(f'class:capacity:{nameid}'):
        raise ValueError('nonexistent class')
    return nameid

def check_existent_manipulation(nameids):
    for nameid in nameids:
        if not rdbconn.exists(f'class:manipulation:{nameid}'):
            raise ValueError('nonexistent class')
        return nameid

def check_existent_translation(nameids):
    for nameid in nameids:
        if not rdbconn.exists(f'class:translation:{nameid}'):
            raise ValueError('nonexistent class')
        return nameids

def check_existent_sipprofile(nameid):
    if not rdbconn.exists(f'sipprofile:{nameid}'):
        raise ValueError('nonexistent sipprofile')
    return nameid

def check_cluster_node(nodes):
    for node in nodes:
        if node != '_ALL_' and node not in CLUSTERMEMBERS:
            raise ValueError('nonexistent node')
    return nodes

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# GATEWAY
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
class TransportEnum(str, Enum):
    UDP = "UDP"
    TCP = "TCP"
    TLS = "TLS"

class GatewayModel(BaseModel):
    name: str = Field(regex=_NAME_, max_length=32, description='name of translation class')
    desc: Optional[str] = Field(default='', max_length=64, description='description')
    ip: IPv4Address = Field(description='farend ip address')
    port: int = Field(ge=0, le=65535, description='farend destination port')
    transport: TransportEnum = Field(default=TransportEnum.UDP, description='farend transport protocol')
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


@librerouter.post("/libresbc/gateway", status_code=200)
def create_gateway(reqbody: GatewayModel, response: Response):
    result = None
    try:
        name = reqbody.name
        data = jsonable_encoder(reqbody)
        name_key = f'gateway:{name}'
        if rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent gateway name'}; return
        rdbconn.hmset(name_key, redishash(data))
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_gateway, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.put("/libresbc/gateway/{identifier}", status_code=200)
def update_gateway(reqbody: GatewayModel, identifier: str, response: Response):
    result = None
    try:
        name = reqbody.name
        data = jsonable_encoder(reqbody)
        _name_key = f'gateway:{identifier}'
        _engaged_key = f'engagement:{_name_key}'
        name_key = f'gateway:{name}'
        engaged_key = f'engagement:{name_key}'
        if not rdbconn.exists(_name_key): 
            response.status_code, result = 403, {'error': 'nonexistent gateway identifier'}; return
        if name != identifier and rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent gateway name'}; return
        rdbconn.hmset(name_key, redishash(data))
        if name != identifier:
            engagements = rdbconn.smembers(_engaged_key)
            for engagement in engagements:
                weight = rdbconn.hget(f'intcon:out:{engagement}', identifier)
                pipe.hget(f'intcon:out:{engagement}', name, weight)
                pipe.hdel(f'intcon:out:{engagement}', identifier)
            if rdbconn.exists(_engaged_key):
                pipe.rename(_engaged_key, engaged_key)
            pipe.delete(_name_key)
            pipe.execute()
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=update_gateway, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.delete("/libresbc/gateway/{identifier}", status_code=200)
def delete_gateway(identifier: str, response: Response):
    result = None
    try:
        _name_key = f'gateway:{identifier}'
        _engaged_key = f'engagement:{_name_key}'
        if rdbconn.scard(_engaged_key): 
            response.status_code, result = 403, {'error': 'engaged gateway'}; return
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent gateway identifier'}; return
        pipe.delete(_engaged_key)
        pipe.delete(_name_key)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=delete_gateway, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libresbc/gateway/{identifier}", status_code=200)
def detail_gateway(identifier: str, response: Response):
    result = None
    try:
        _name_key = f'gateway:{identifier}'
        _engaged_key = f'engagement:{_name_key}'
        if not rdbconn.exists(_name_key): 
            response.status_code, result = 403, {'error': 'nonexistent gateway identifier'}; return
        result = jsonhash(rdbconn.hgetall(_name_key))
        engagements = rdbconn.smembers(_engaged_key)
        result.update({'engagements': engagements})
        response.status_code = 200
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=detail_gateway, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libresbc/gateway", status_code=200)
def list_gateway(response: Response):
    result = None
    try:
        KEYPATTERN = f'gateway:*'
        next, mainkeys = rdbconn.scan(0, KEYPATTERN, SCAN_COUNT)
        while next:
            next, tmpkeys = rdbconn.scan(next, KEYPATTERN, SCAN_COUNT)
            mainkeys += tmpkeys

        for mainkey in mainkeys:
            pipe.hmget(mainkey, 'desc', 'ip', 'port', 'transport')
        details = pipe.execute()

        data = list()
        for mainkey, detail in zip(mainkeys, details):
            if detail:
                data.append({'name': getnameid(mainkey), 'desc': detail[0], 'ip': detail[1], 'port': detail[2], 'transport': detail[3]})

        response.status_code, result = 200, data
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=list_gateway, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# OUTBOUND INTERCONECTION
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------

class Distribution(str, Enum):
    round_robin = 'round_robin'
    hash_caller = 'hash_caller'
    hash_callee = 'hash_callee'
    hash_both = 'hash_both'
    hash_callid = 'hash_callid'
    weight_based = 'weight_based'

def check_existent_gateway(gateway):
    if not rdbconn.exists(f'gateway:{gateway}'):
        raise ValueError('nonexistent gateway')
    return gateway

class GatewayWeightModel(BaseModel):
    gateway: str = Field(description='outbound gateway name')
    weight: int = Field(default=1, ge=0, le=99, description='weight based load distribution')
    # validation
    _existentgateway = validator('gateway')(check_existent_gateway)

class OutboundInterconnection(BaseModel):
    name: str = Field(regex=_NAME_, max_length=32, description='name of outbound interconnection')
    desc: Optional[str] = Field(default='', max_length=64, description='description')
    sipprofile: str = Field(description='a sip profile nameid that interconnection engage to')
    distribution: Distribution = Field(default='round_robin', description='The dispatcher algorithm to selects a destination from addresses set')
    gateways: List[GatewayWeightModel] = Field(min_items=1, max_item=10, description='list of outbound gateways')
    rtp_nets: List[IPv4Network] = Field(min_items=1, max_item=20, description='a set of IPv4 Network that use for RTP')
    codec_class: str = Field(description='nameid of codec class')
    capacity_class: str = Field(description='nameid of capacity class')
    translation_classes: List[str] = Field(default=[], min_items=0, max_item=5, description='a set of translation class')
    manipulation_classes: List[str] = Field(default=[], min_items=0, max_item=5, description='a set of manipulations class')
    nodes: List[str] = Field(default=['_ALL_'], min_items=1, max_item=len(CLUSTERMEMBERS), description='a set of node member that interconnection engage to')
    enable: bool = Field(default=True, description='enable/disable this interconnection')
    # validation
    _existentcodec = validator('codec_class', allow_reuse=True)(check_existent_codec)
    _existentcapacity = validator('capacity_class', allow_reuse=True)(check_existent_capacity)
    _existenttranslation = validator('translation_classes', allow_reuse=True)(check_existent_translation)
    _existentmanipulation = validator('manipulation_classes', allow_reuse=True)(check_existent_translation)
    _existentsipprofile = validator('sipprofile', allow_reuse=True)(check_existent_sipprofile)
    _clusternode = validator('nodes', allow_reuse=True)(check_cluster_node)


@librerouter.post("/libresbc/interconnection/outbound", status_code=200)
def create_outbound_interconnection(reqbody: OutboundInterconnection, response: Response):
    result = None
    try:
        name = reqbody.name
        data = jsonable_encoder(reqbody)
        sipprofile = data.get('sipprofile')
        gateways = data.get('gateways')
        rtp_nets = set(data.get('rtp_nets'))
        codec_class = data.get('codec_class')
        capacity_class = data.get('capacity_class')
        translation_classes = data.get('translation_classes')
        manipulation_classes = data.get('manipulation_classes')
        nodes = set(data.get('nodes'))
        # verification
        nameid = f'out:{name}'; name_key = f'intcon:{nameid}'
        if rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent outbound interconnection'}; return
        # processing
        data.pop('gateways'); data.update({'rtp_nets': rtp_nets, 'nodes': nodes })
        pipe.hmset(name_key, redishash(data))
        pipe.sadd(f'engagement:sipprofile:{sipprofile}', nameid)
        for node in nodes: pipe.sadd(f'engagement:node:{node}', nameid)
        pipe.sadd(f'engagement:codec:{codec_class}', nameid)
        pipe.sadd(f'engagement:capacity:{capacity_class}', nameid)
        for translation in translation_classes: pipe.sadd(f'engagement:translation:{translation}', nameid)
        for manipulation in manipulation_classes: pipe.sadd(f'engagement:manipulation:{manipulation}', nameid)
        pipe.hmset(f'intcon:{nameid}:gateways', redishash(gateways))
        for gateway in gateways: pipe.sadd(f'engagement:gateway:{gateway}', name)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_outbound_interconnection, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.post("/libresbc/interconnection/outbound/{identifier}", status_code=200)
def update_outbound_interconnection(reqbody: OutboundInterconnection, identifier: str, response: Response):
    result = None
    try:
        name = reqbody.name
        data = jsonable_encoder(reqbody)
        sipprofile = data.get('sipprofile')
        gateways = data.get('gateways')
        rtp_nets = set(data.get('rtp_nets'))
        codec_class = data.get('codec_class')
        capacity_class = data.get('capacity_class')
        translation_classes = data.get('translation_classes')
        manipulation_classes = data.get('manipulation_classes')
        nodes = set(data.get('nodes'))
        # verification
        nameid = f'out:{name}'; name_key = f'intcon:{nameid}';
        _nameid = f'out:{identifier}'; _name_key = f'intcon:{_nameid}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent outbound interconnection identifier'}; return
        if name != identifier and rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent outbound interconnection name'}; return
        # get current data
        _data = jsonhash(rdbconn.hgetall(_name_key))
        _sipprofile = _data.get('sipprofile')
        _nodes = _data.get('nodes')
        _codec_class = _data.get('codec_class')
        _capacity_class = _data.get('capacity_class')
        _translation_classes = _data.get('translation_classes')
        _manipulation_classes = _data.get('manipulation_classes')
        _sip_ips = _data.get('sip_ips')
        _gateways = jsonhash(rdbconn.hgetall(f'intcon:{nameid}:gateways'))
        # transaction block
        pipe.multi()
        # processing: removing old-one
        pipe.srem(f'engagement:sipprofile:{_sipprofile}', _nameid)
        for node in _nodes: pipe.srem(f'engagement:node:{node}', _nameid)
        pipe.srem(f'engagement:codec:{_codec_class}', _nameid)
        pipe.srem(f'engagement:capacity:{_capacity_class}', _nameid)
        for translation in _translation_classes: pipe.srem(f'engagement:translation:{translation}', _nameid)
        for manipulation in _manipulation_classes: pipe.srem(f'engagement:manipulation:{manipulation}', _nameid)
        for gateway in _gateways: pipe.srem(f'engagement:gateway:{gateway}', identifier)
        pipe.delete(f'intcon:{_nameid}:gateways')
        # processing: adding new-one
        data.pop('gateways'); data.update({'rtp_nets': rtp_nets, 'nodes': nodes })
        pipe.hmset(name_key, redishash(data))
        pipe.sadd(f'engagement:sipprofile:{sipprofile}', nameid)
        for node in nodes: pipe.sadd(f'engagement:node:{node}', nameid)
        pipe.sadd(f'engagement:codec:{codec_class}', nameid)
        pipe.sadd(f'engagement:capacity:{capacity_class}', nameid)
        for translation in translation_classes: pipe.sadd(f'engagement:translation:{translation}', nameid)
        for manipulation in manipulation_classes: pipe.sadd(f'engagement:manipulation:{manipulation}', nameid)
        pipe.hmset(f'intcon:{nameid}:gateways', redishash(gateways))
        for gateway in gateways: pipe.sadd(f'engagement:gateway:{gateway}', name)
        # change identifier
        if name != identifier:
            pipe.delete(_name_key)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=update_outbound_interconnection, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.delete("/libresbc/interconnection/outbound/{identifier}", status_code=200)
def delete_outbound_interconnection(identifier: str, response: Response):
    result = None
    try:
        _nameid = f'out:{identifier}'; _name_key = f'intcon:{_nameid}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent outbound interconnection identifier'}; return
        # get current data
        _data = jsonhash(rdbconn.hgetall(_name_key))
        _sipprofile = _data.get('sipprofile')
        _nodes = _data.get('nodes')
        _codec_class = _data.get('codec_class')
        _capacity_class = _data.get('capacity_class')
        _translation_classes = _data.get('translation_classes')
        _manipulation_classes = _data.get('manipulation_classes')
        _sip_ips = _data.get('sip_ips')
        _gateways = jsonhash(rdbconn.hgetall(f'intcon:{nameid}:gateways'))
        # processing: removing old-one
        pipe.srem(f'engagement:sipprofile:{_sipprofile}', _nameid)
        for node in _nodes: pipe.srem(f'engagement:node:{node}', _nameid)
        pipe.srem(f'engagement:codec:{_codec_class}', _nameid)
        pipe.srem(f'engagement:capacity:{_capacity_class}', _nameid)
        for translation in _translation_classes: pipe.srem(f'engagement:translation:{translation}', _nameid)
        for manipulation in _manipulation_classes: pipe.srem(f'engagement:manipulation:{manipulation}', _nameid)
        for gateway in _gateways: pipe.srem(f'engagement:gateway:{gateway}', identifier)
        pipe.delete(f'intcon:{_nameid}:gateways')
        pipe.delete(_name_key)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=delete_outbound_interconnection, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libresbc/interconnection/outbound/{identifier}", status_code=200)
def detail_outbound_interconnection(identifier: str, response: Response):
    result = None
    try:
        _nameid = f'out:{identifier}'
        _name_key = f'intcon:{_nameid}'
        _engaged_key = f'engagement:{_name_key}'
        if not rdbconn.exists(_name_key): 
            response.status_code, result = 403, {'error': 'nonexistent outbound interconnection identifier'}; return
        result = rdbconn.hgetall(_name_key)
        gateways = rdbconn.hgetall(f'intcon:{_nameid}:gateways')
        engagements = rdbconn.smembers(_engaged_key)
        result.update({'gateways': gateways, 'engagements': engagements})
        response.status_code = 200
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=detail_outbound_interconnection, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
@librerouter.get("/libresbc/interconnection/outbound", status_code=200)
def list_outbound_interconnect(response: Response):
    result = None
    try:
        KEYPATTERN = 'intcon:out:*'
        next, mainkeys = rdbconn.scan(0, KEYPATTERN, SCAN_COUNT)
        while next:
            next, tmpkeys = rdbconn.scan(next, KEYPATTERN, SCAN_COUNT)
            mainkeys += tmpkeys

        for mainkey in mainkeys:
            pipe.hmget(mainkey, 'name', 'desc', 'sipprofile')
        details = pipe.execute()

        data = list()
        for mainkey, detail in zip(mainkeys, details):
            data.append({'name': getnameid(mainkey), 'desc': detail[0], 'sipprofile': detail[1]})

        response.status_code, result = 200, data
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=list_outbound_interconnect, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# INBOUND INTERCONECTION
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------

def check_existent_routing(table):
    if not rdbconn.exists(f'routing:{table}'):
        raise ValueError('nonexistent routing')
    return table

class InboundInterconnection(BaseModel):
    name: str = Field(regex=_NAME_, max_length=32, description='name of inbound interconnection')
    desc: Optional[str] = Field(default='', max_length=64, description='description')
    sipprofile: str = Field(description='a sip profile nameid that interconnection engage to')
    routing: str = Field(description='routing table that will be used by this inbound interconnection') 
    sip_ips: List[IPv4Address] = Field(min_items=1, max_item=10, description='a set of signalling that use for SIP')
    rtp_nets: List[IPv4Network] = Field(min_items=1, max_item=20, description='a set of IPv4 Network that use for RTP')
    codec_class: str = Field(description='nameid of codec class')
    capacity_class: str = Field(description='nameid of capacity class')
    translation_classes: List[str] = Field(default=[], min_items=0, max_item=5, description='a set of translation class')
    manipulation_classes: List[str] = Field(default=[], min_items=0, max_item=5, description='a set of manipulations class')
    nodes: List[str] = Field(default=['_ALL_'], min_items=1, max_item=len(CLUSTERMEMBERS), description='a set of node member that interconnection engage to')
    enable: bool = Field(default=True, description='enable/disable this interconnection')
    # validation
    _existentcodec = validator('codec_class', allow_reuse=True)(check_existent_codec)
    _existentcapacity = validator('capacity_class', allow_reuse=True)(check_existent_capacity)
    _existenttranslation = validator('translation_classes', allow_reuse=True)(check_existent_translation)
    _existentmanipulation = validator('manipulation_classes', allow_reuse=True)(check_existent_translation)
    _existentsipprofile = validator('sipprofile', allow_reuse=True)(check_existent_sipprofile)
    _existentrouting = validator('routing')(check_existent_routing)
    _clusternode = validator('nodes', allow_reuse=True)(check_cluster_node)


@librerouter.post("/libresbc/interconnection/inbound", status_code=200)
def create_inbound_interconnection(reqbody: InboundInterconnection, response: Response):
    result = None
    try:
        name = reqbody.name
        data = jsonable_encoder(reqbody)
        sipprofile = data.get('sipprofile')
        routing = data.get('routing')
        sip_ips = set(data.get('sip_ips'))
        rtp_nets = set(data.get('rtp_nets'))
        codec_class = data.get('codec_class')
        capacity_class = data.get('capacity_class')
        translation_classes = data.get('translation_classes')
        manipulation_classes = data.get('manipulation_classes')
        nodes = set(data.get('nodes'))
        # verification
        nameid = f'in:{name}'; name_key = f'intcon:{nameid}'
        if rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent inbound interconnection'}; return
        for sip_ip in sip_ips:
            if rdbconn.exists(f'recognition:{sipprofile}:{sip_ip}'):
                response.status_code, result = 403, {'error': 'existent sip ip'}; return
        # processing
        data.update({'sip_ips': sip_ips, 'rtp_nets': rtp_nets, 'nodes': nodes })
        pipe.hmset(name_key, redishash(data))
        pipe.sadd(f'engagement:sipprofile:{sipprofile}', nameid)
        pipe.sadd(f'engagement:routing:{routing}', nameid)
        for node in nodes: pipe.sadd(f'engagement:node:{node}', nameid)
        pipe.sadd(f'engagement:codec:{codec_class}', nameid)
        pipe.sadd(f'engagement:capacity:{capacity_class}', nameid)
        for translation in translation_classes: pipe.sadd(f'engagement:translation:{translation}', nameid)
        for manipulation in manipulation_classes: pipe.sadd(f'engagement:manipulation:{manipulation}', nameid)
        for sip_ip in sip_ips: pipe.set(f'recognition:{sipprofile}:{sip_ip}', name)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_inbound_interconnection, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


@librerouter.put("/libresbc/interconnection/inbound/{identifier}", status_code=200)
def update_inbound_interconnection(reqbody: InboundInterconnection, identifier: str, response: Response):
    result = None
    try:
        name = reqbody.name
        data = jsonable_encoder(reqbody)
        sipprofile = data.get('sipprofile')
        sip_ips = set(data.get('sip_ips'))
        rtp_nets = set(data.get('rtp_nets'))
        routing = data.get('routing')
        codec_class = data.get('codec_class')
        capacity_class = data.get('capacity_class')
        translation_classes = data.get('translation_classes')
        manipulation_classes = data.get('manipulation_classes')
        nodes = set(data.get('nodes'))
        # verification
        nameid = f'in:{name}'; name_key = f'intcon:{nameid}'
        _nameid = f'in:{identifier}'; _name_key = f'intcon:{_nameid}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent inbound interconnection identifier'}; return
        if name != identifier and rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent inbound interconnection name'}; return
        for sip_ip in sip_ips:
            _name = rdbconn.exists(f'recognition:{sipprofile}:{sip_ip}')
            if _name and _name != name:
                response.status_code, result = 403, {'error': 'existent sip ip'}; return
        # get current data
        _data = jsonhash(rdbconn.hgetall(_name_key))
        _sipprofile = _data.get('sipprofile')
        _routing = _data.get('routing')
        _nodes = set(_data.get('nodes'))
        _codec_class = _data.get('codec_class')
        _capacity_class = _data.get('capacity_class')
        _translation_classes = _data.get('translation_classes')
        _manipulation_classes = _data.get('manipulation_classes')
        _sip_ips = set(_data.get('sip_ips'))
        # transaction block
        pipe.multi()
        # processing: removing old-one
        pipe.srem(f'engagement:sipprofile:{_sipprofile}', _nameid)
        pipe.srem(f'engagement:routing:{_routing}', _nameid)
        for node in _nodes: pipe.srem(f'engagement:node:{node}', _nameid)
        pipe.srem(f'engagement:codec:{_codec_class}', _nameid)
        pipe.srem(f'engagement:capacity:{_capacity_class}', _nameid)
        for translation in _translation_classes: pipe.srem(f'engagement:translation:{translation}', _nameid)
        for manipulation in _manipulation_classes: pipe.srem(f'engagement:manipulation:{manipulation}', _nameid)
        for sip_ip in _sip_ips: pipe.delete(f'recognition:{_sipprofile}:{sip_ip}') 
        # processing: adding new-one
        data.update({'sip_ips': sip_ips, 'rtp_nets': rtp_nets, 'nodes': nodes })
        pipe.hmset(name_key, redishash(data))
        pipe.sadd(f'engagement:sipprofile:{sipprofile}', nameid)
        pipe.sadd(f'engagement:routing:{routing}', nameid)
        for node in nodes: pipe.sadd(f'engagement:node:{node}', nameid)
        pipe.sadd(f'engagement:codec:{codec_class}', nameid)
        pipe.sadd(f'engagement:capacity:{capacity_class}', nameid)
        for translation in translation_classes: pipe.sadd(f'engagement:translation:{translation}', nameid)
        for manipulation in manipulation_classes: pipe.sadd(f'engagement:manipulation:{manipulation}', nameid)
        for sip_ip in sip_ips: pipe.set(f'recognition:{sipprofile}:{sip_ip}', name)   
        # change identifier
        if name != identifier:
            pipe.delete(_name_key)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=update_inbound_interconnection, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


@librerouter.delete("/libresbc/interconnection/inbound/{identifier}", status_code=200)
def delete_inbound_interconnection(identifier: str, response: Response):
    result = None
    try:
        _nameid = f'in:{identifier}'; _name_key = f'intcon:{_nameid}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent inbound interconnection'}; return

        _data = jsonhash(rdbconn.hgetall(_name_key))
        _sipprofile = _data.get('sipprofile')
        _nodes = _data.get('nodes')
        _codec_class = _data.get('codec_class')
        _capacity_class = _data.get('capacity_class')
        _translation_classes = _data.get('translation_classes')
        _manipulation_classes = _data.get('manipulation_classes')
        _sip_ips = _data.get('sip_ips')

        pipe.srem(f'engagement:sipprofile:{_sipprofile}', _nameid)
        for node in _nodes: pipe.srem(f'engagement:node:{node}', _nameid)
        pipe.srem(f'engagement:codec:{_codec_class}', _nameid)
        pipe.srem(f'engagement:capacity:{_capacity_class}', _nameid)
        for translation in _translation_classes: pipe.srem(f'engagement:translation:{translation}', _nameid)
        for manipulation in _manipulation_classes: pipe.srem(f'engagement:manipulation:{manipulation}', _nameid)
        for sip_ip in _sip_ips: pipe.delete(f'recognition:{_sipprofile}:{sip_ip}')  
        pipe.delete(_name_key)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=delete_inbound_interconnection, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


@librerouter.get("/libresbc/interconnection/inbound/{identifier}", status_code=200)
def detail_inbound_interconnection(identifier: str, response: Response):
    result = None
    try:
        _name_key = f'intcon:in:{identifier}'
        if not rdbconn.exists(_name_key): 
            response.status_code, result = 403, {'error': 'nonexistent inbound interconnection identifier'}; return
        result = rdbconn.hgetall(_name_key)
        response.status_code = 200
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=detail_inbound_interconnection, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


@librerouter.get("/libresbc/interconnection/inbound", status_code=200)
def list_inbound_interconnect(response: Response):
    result = None
    try:
        KEYPATTERN = 'intcon:in:*'
        next, mainkeys = rdbconn.scan(0, KEYPATTERN, SCAN_COUNT)
        while next:
            next, tmpkeys = rdbconn.scan(next, KEYPATTERN, SCAN_COUNT)
            mainkeys += tmpkeys

        for mainkey in mainkeys:
            pipe.hmget(mainkey, 'desc', 'sipprofile', 'routing')
        details = pipe.execute()

        data = list()
        for mainkey, detail in zip(mainkeys, details):
            data.append({'name': getnameid(mainkey), 'desc': detail[0], 'sipprofile': detail[1], 'routing': detail[2]})

        response.status_code, result = 200, data
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=list_inbound_interconnect, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result



#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ROUTING TABLE
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
_QUERY_ = '_QUERY_'
_BLOCK_ = '_BLOCK_'
_JUMPS_ = '_JUMPS:'
CONSTROUTE = [_QUERY_, _BLOCK_]

class RoutingVariableEnum(str, Enum):
    _any_ = '_any_'
    destination_number = 'destination_number'
    caller_id = 'caller_id'
    auth_user = 'auth_user'
    from_user = 'from_user'
    to_user = 'to_user'
    contact_user = 'contact_user'

def check_valid_nexthop_table(nexthop):
    if nexthop not in [_QUERY_, _BLOCK_] and not rdbconn.exists(f'intcon:out:{nexthop}'):
        raise ValueError('nonexistent outbound interconnect')
    return nexthop

class RoutingTableModel(BaseModel):
    name: str = Field(regex=_NAME_, max_length=32, description='name of routing table')
    desc: Optional[str] = Field(default='', max_length=64, description='description')
    variables: List[RoutingVariableEnum] = Field(min_items=1, max_items=1, description='sip variable for routing base')
    nexthop: str = Field(description=f'{_QUERY_}: query nexthop; {_BLOCK_}: block the call; INTERCONNECTION: dirrect nexthop')
    # validation
    _nexthoptable = validator('nexthop')(check_valid_nexthop_table)

@librerouter.post("/libresbc/routing/table", status_code=200)
def create_routing_table(reqbody: RoutingTableModel, response: Response):
    result = None
    try:
        name = reqbody.name
        nexthop = reqbody.nexthop
        data = jsonable_encoder(reqbody)
        name_key = f'routing:table:{name}'
        if rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent routing table'}; return
        pipe.hmset(name_key, redishash(data))
        if nexthop not in CONSTROUTE: pipe.sadd(f'egagement:intcon:out:{nexthop}', name)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_routing_table, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.put("/libresbc/routing/table/{identifier}", status_code=200)
def update_routing_table(reqbody: RoutingTableModel, identifier: str, response: Response):
    result = None
    try:
        name = reqbody.name
        nexthop = reqbody.nexthop
        data = jsonable_encoder(reqbody)
        _name_key = f'routing:table:{identifier}'
        _engaged_key = f'engagement:{_name_key}'
        name_key = f'routing:table:{name}'
        engaged_key = f'engagement:{name_key}'
        if not rdbconn.exists(_name_key): 
            response.status_code, result = 403, {'error': 'nonexistent routing table identifier'}; return
        if name != identifier and rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent routing table name'}; return
        # get current data
        _nexthop = rdbconn.hget(_name_key, 'nexthop')
        # transaction block
        pipe.multi()
        pipe.srem(f'egagement:intcon:out:{nexthop}', identifier)
        pipe.hmset(name_key, redishash(data))
        if nexthop not in CONSTROUTE: pipe.sadd(f'egagement:intcon:out:{nexthop}', name)
        if name != identifier:
            engagements = rdbconn.smembers(_engaged_key)
            for engagement in engagements:
                pipe.hset(f'intcon:in:{engagement}', 'routing', name)
            if rdbconn.exists(_engaged_key):
                pipe.rename(_engaged_key, engaged_key)
            pipe.delete(_name_key)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=update_routing_table, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.delete("/libresbc/routing/table/{identifier}", status_code=200)
def delete_routing_table(identifier: str, response: Response):
    result = None
    try:
        _name_key = f'routing:table:{identifier}'
        _engaged_key = f'engagement:{_name_key}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent routing table'}; return
        if rdbconn.scard(_engaged_key): 
            response.status_code, result = 403, {'error': 'engaged routing table'}; return
        # check if routing records exists in table
        _ROUTING_KEY_PATTERN = f'routing:record:{identifier}:*'
        next, records = rdbconn.scan(0, _ROUTING_KEY_PATTERN, SCAN_COUNT)
        if records:
            response.status_code, result = 400, {'error': 'routing table in used'}; return
        else:
            while next:
                next, records = rdbconn.scan(next, _ROUTING_KEY_PATTERN, SCAN_COUNT)
                if records:
                    response.status_code, result = 400, {'error': 'routing table in used'}; return
        # process
        pipe.delete(_engaged_key)
        pipe.delete(_name_key)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=delete_routing_table, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libresbc/routing/table/{identifier}", status_code=200)
def detail_routing_table(identifier: str, response: Response):
    result = None
    try:
        _name_key = f'routing:table:{identifier}'
        _engaged_key = f'engagement:{_name_key}'
        if not rdbconn.exists(_name_key): 
            response.status_code, result = 403, {'error': 'nonexistent routing table identifier'}; return
        result = jsonhash(rdbconn.hgetall(_name_key))
        engagements = rdbconn.smembers(_engaged_key)
        result.update({'engagements': engagements})
        response.status_code = 200
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=detail_routing_table, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libresbc/routing/table", status_code=200)
def list_routing_table(response: Response):
    result = None
    try:
        KEYPATTERN = f'routing:table:*'
        next, mainkeys = rdbconn.scan(0, KEYPATTERN, SCAN_COUNT)
        while next:
            next, tmpkeys = rdbconn.scan(next, KEYPATTERN, SCAN_COUNT)
            mainkeys += tmpkeys

        for mainkey in mainkeys: pipe.hgetall(mainkey)
        details = pipe.execute()

        data = list()
        for mainkey, detail in zip(mainkeys, details):
            data.append(jsonhash(detail))

        response.status_code, result = 200, data
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=list_routing_table, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ROUTING RECORD
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------

class MatchingEnum(str, Enum):
    lpm = 'lpm'
    em = 'em'

class RoutingRecordModel(BaseModel):
    table: str = Field(regex=_NAME_, max_length=32, description='name of routing table')
    match: MatchingEnum = Field(description='matching options, include lpm: longest prefix match, em: exact match')
    value: str = Field(max_length=32, description='value of factor')
    nexthop1st: str = Field(description=f'{_JUMPS_}:TABLE jumps to other routing table; {_BLOCK_}: block the call; INTERCONNECTION: dirrect nexthop')
    nexthop2nd: str = Field(description=f'{_JUMPS_}:TABLE jumps to other routing table; {_BLOCK_}: block the call; INTERCONNECTION: dirrect nexthop')
    load: int = Field(default=100, ge=0, le=100, description='call load percentage over total 100, that apply for nexthop1st')
    # validation
    @validator(...)
    def record_agrement(cls, values):
        table = values.get('table')
        nexthop1st = values.get('nexthop1st')
        nexthop2nd = values.get('nexthop2nd')

        if not rdbconn.exists(f'routing:table:{table}'):
            raise ValueError('nonexistent routing table')
        for nexthop in [nexthop1st, nexthop2nd]:
            if nexthop.startwiths(_JUMPS_):
                nexttable = getnameid(nexthop)
                if not rdbconn.exists(f'routing:table:{nexttable}'): 
                    raise ValueError('nonexistent routing table for nexthop')
            else:
                if nexthop != _BLOCK_ and not rdbconn.exists(f'intcon:out:{nexthop}'):
                    raise ValueError('nonexistent outbound interconnect')
        if nexthop1st.startwiths('_') or nexthop2nd.startwiths('_'):
            if nexthop1st != nexthop2nd: 
                raise ValueError('nexthops are not the same type')

        return nexthop

@app.api_route("/test", methods=["GET", "POST", "DELETE"])
async def test(request: Request):
    return {"method": request.method}

@librerouter.api_route("/libresbc/routing/record", methods=["PUT", "POST"], status_code=200)
def define_routing_record(request: Request, reqbody: RoutingRecordModel, response: Response):
    result = None
    try:
        table = reqbody.table
        match = reqbody.match
        value = reqbody.value
        nexthop1st = reqbody.nexthop1st
        nexthop2nd = reqbody.tanexthop2nd
        load = reqbody.load

        record = f'{table}:{match}:{value}'; record_key = f'routing:record:{record}'
        record_exists = rdbconn.exists(record_key)
        if request.method=='POST':
            if record_exists:
                response.status_code, result = 403, {'error': 'existent routing record'}; return
        else:
            if not record_exists:
                response.status_code, result = 403, {'error': 'non existent routing record'}; return

        pipe.hmset(record_key, redishash({'nexthop1st': nexthop1st, 'nexthop2nd': nexthop2nd, 'load': load}))
        for nexthop in [nexthop1st, nexthop2nd]:
            if nexthop not in CONSTROUTE:
                if nexthop.startwiths(_JUMPS_):
                    nexttable = getnameid(nexthop)
                    pipe.sadd(f'egagement:routing:table:{table}', nexttable)
                else:
                    pipe.sadd(f'egagement:intcon:out:{nexthop}', record)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=define_routing_record, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.delete("/libresbc/routing/record/{table}/{match}:{value}:", status_code=200)
def delete_routing_record(response: Response, value:str, table:str=Path(..., regex=_NAME_), match:str=Path(..., regex='^(em|lpm)$')):
    result = None
    try:
        record = f'{table}:{match}:{value}'; record_key = f'routing:record:{record}'
        if not rdbconn.exists(record_key):
            response.status_code, result = 403, {'error': 'notexistent routing record'}; return

        _data = jsonhash(rdbconn.hgetall(record_key))
        _nexthop1st = _data.get('nexthop1st')
        _nexthop2nd = _data.get('nexthop2nd')

        pipe.delete(record_key)
        for nexthop in [_nexthop1st, _nexthop2nd]:
            if nexthop not in CONSTROUTE:
                if nexthop.startwiths(_JUMPS_):
                    nexttable = getnameid(nexthop)
                    pipe.srem(f'egagement:routing:table:{table}', nexttable)
                else:
                    pipe.srem(f'egagement:intcon:out:{nexthop}', record)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=delete_routing_record, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libresbc/routing/record/{table}:", status_code=200)
def list_routing_record(response: Response, table:str=Path(..., regex=_NAME_)):
    result = None
    try:
        if not rdbconn.exists(f'routing:table:{table}'): 
            response.status_code, result = 403, {'error': 'nonexistent routing table identifier'}; return

        KEYPATTERN = f'routing:record:{table}:*'
        next, mainkeys = rdbconn.scan(0, KEYPATTERN, SCAN_COUNT)
        while next:
            next, tmpkeys = rdbconn.scan(next, KEYPATTERN, SCAN_COUNT)
            mainkeys += tmpkeys

        for mainkey in mainkeys: pipe.hgetall(mainkey)
        details = pipe.execute()

        data = list()
        for mainkey, detail in zip(mainkeys, details):
            records = listify(mainkey)
            detail.update({'match': records[-2], 'value': records[-1]})
            data.append(jsonhash(detail))

        response.status_code, result = 200, data
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=list_routing_record, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result