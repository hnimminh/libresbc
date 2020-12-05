import traceback
import re
import json

import redis
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from enum import Enum
from ipaddress import IPv4Address, IPv4Network
from fastapi import APIRouter, Request, Response

from configuration import (_APPLICATION, _SWVERSION, _DESCRIPTION, NODENAME, CLUSTERNAME, CLUSTERMEMBERS,
                           SWCODECS, MAX_CPS, MAX_ACTIVE_SESSION,
                           REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD, SCAN_COUNT)
from utilities import logify, debugy, get_request_uuid, int2bool, bool2int, rembytes, guid


REDIS_CONNECTION_POOL = redis.BlockingConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD, 
                                                     max_connections=10, timeout=5)
rdbconn = redis.StrictRedis(connection_pool=REDIS_CONNECTION_POOL)                                                    
pipe = rdbconn.pipeline()

# PATTERN
_NAME_ = '^[a-zA-Z][a-zA-Z0-9_]+$'; _NAME_PATTERN = re.compile(_NAME_)
_DIAL_ = '^[a-zA-Z0-9+#*]*$'; _DIAL_PATTERN = re.compile(_DIAL_)

# api router declaration
librerouter = APIRouter()
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------

@librerouter.get("/predefine", status_code=200)
def predefine():
    return {
        "nodename": NODENAME,
        "cluster": CLUSTERNAME,
        "application": _APPLICATION,
        'swversion': _SWVERSION,
        "description": _DESCRIPTION
    }

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


@librerouter.post("/class/codec", status_code=200)
def create_codec_class(req_body: CodecModel, response: Response):
    result = None
    try:
        name = req_body.name
        desc = req_body.desc
        data = req_body.data
        uuid = guid()
        key = f'class:codec:{uuid}'
        if rdbconn.exists(key): 
            response.status_code, result = 400, {'error': 'existent_class'}; return
        rdbconn.hmset(key, {'name': name, 'desc': desc, 'data': json.dumps(data)})
        response.status_code, result = 200, {'uuid': uuid}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_codec_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.put("/class/codec/{uuid}", status_code=200)
def update_codec_class(req_body: CodecModel, uuid: str, response: Response):
    result = None
    try:
        name = req_body.name
        desc = req_body.desc
        data = req_body.data
        key = f'class:codec:{uuid}'
        if not rdbconn.exists(key): 
            response.status_code, result = 400, {'error': 'nonexistent_class'}; return
        rdbconn.hmset(key, {'desc': desc, 'data': json.dumps(data)})
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=update_codec_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.delete("/class/codec/{uuid}", status_code=200)
def delete_codec_class(uuid: str, response: Response):
    result = None
    try:
        if rdbconn.scard(f'engagement:codec:{uuid}'): 
            response.status_code, result = 403, {'error': 'enageged_class'}; return
        classkey = f'class:codec:{uuid}'
        if not rdbconn.exists(classkey): 
            response.status_code, result = 400, {'error': 'nonexistent_class'}; return
        rdbconn.delete(classkey)
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=delete_codec_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/class/codec/{uuid}", status_code=200)
def detail_codec_class(uuid: str, response: Response):
    result = None
    try:
        classkey = f'class:codec:{uuid}'
        if not rdbconn.exists(classkey): 
            response.status_code, result = 400, {'error': 'nonexistent_class'}; return
        data = rdbconn.hgetall(classkey)
        engagements = rembytes(rdbconn.smembers(f'engagement:codec:{uuid}'))
        data.update({'engagements': engagements})
        response.status_code, result = 200, data
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=detail_codec_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/class/codec", status_code=200)
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
                uuid = mainkey.decode().split(':')[-1]
                detail.update({'uuid': uuid})
                data.append(detail)

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
    cps: int = Field(default=2, ge=1, le=len(CLUSTERMEMBERS)*MAX_CPS/2, description='call per second')
    capacity: int = Field(default=10, ge=1, le=len(CLUSTERMEMBERS)*MAX_ACTIVE_SESSION/2, description='concurernt call')


@librerouter.post("/class/capacity", status_code=200)
def create_capacity_class(req_body: CapacityModel, response: Response):
    result = None
    try:
        name = req_body.name
        desc = req_body.desc
        cps = req_body.cps
        capacity = req_body.capacity
        uuid = guid()
        key = f'class:capacity:{uuid}'
        if rdbconn.exists(key): 
            response.status_code, result = 400, {'error': 'existent_class'}; return
        rdbconn.hmset(key, {'name': name, 'desc': desc, 'cps': cps, 'capacity': capacity})
        response.status_code, result = 200, {'uuid': uuid}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_capacity_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.put("/class/capacity/{uuid}", status_code=200)
def update_capacity_class(req_body: CapacityModel, uuid: str, response: Response):
    result = None
    try:
        name = req_body.name
        desc = req_body.desc
        cps = req_body.cps
        capacity = req_body.capacity
        key = f'class:capacity:{uuid}'
        if not rdbconn.exists(key): 
            response.status_code, result = 400, {'error': 'nonexistent_class'}; return
        rdbconn.hmset(key, {'name': name, 'desc': desc, 'cps': cps, 'capacity': capacity})
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=update_capacity_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.delete("/class/capacity/{uuid}", status_code=200)
def delete_capacity_class(uuid: str, response: Response):
    result = None
    try:
        if rdbconn.scard(f'engagement:capacity:{id}'): 
            response.status_code, result = 403, {'error': 'enageged_class'}; return
        classkey = f'class:capacity:{id}'
        if not rdbconn.exists(classkey): 
            response.status_code, result = 400, {'error': 'nonexistent_class'}; return
        rdbconn.delete(classkey)
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=delete_capacity_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/class/capacity/{uuid}", status_code=200)
def detail_capacity_class(uuid: str, response: Response):
    result = None
    try:
        classkey = f'class:capacity:{uuid}'
        if not rdbconn.exists(classkey): 
            response.status_code, result = 400, {'error': 'nonexistent_class'}; return
        data = rdbconn.hgetall(classkey)
        engagements = rembytes(rdbconn.smembers(f'engagement:capacity:{uuid}'))
        data.update({'engagements': engagements})
        response.status_code, result = 200, data
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=detail_capacity_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/class/capacity", status_code=200)
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
                uuid = mainkey.decode().split(':')[-1]
                detail.update({'uuid': uuid})
                data.append(detail)

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

@librerouter.post("/class/translation", status_code=200)
def create_translation_class(req_body: TranslationModel, response: Response):
    result = None
    try:
        name = req_body.name
        desc = req_body.desc
        caller_pattern = req_body.caller_pattern
        callee_pattern = req_body.callee_pattern
        caller_replacement = req_body.caller_replacement
        callee_replacement = req_body.callee_replacement
        uuid = guid()
        key = f'class:translation:{uuid}'
        if rdbconn.exists(key): 
            response.status_code, result = 400, {'error': 'existent_class'}; return
        rdbconn.hmset(key, {'name': name, 'desc': desc, 'caller_pattern': caller_pattern, 'callee_pattern': callee_pattern, 
                            'caller_replacement': caller_replacement, 'callee_replacement': callee_replacement})
        response.status_code, result = 200, {'uuid': uuid}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_translation_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.put("/class/translation/{uuid}", status_code=200)
def update_translation_class(req_body: TranslationModel, uuid: str, response: Response):
    result = None
    try:
        name = req_body.name
        desc = req_body.desc
        caller_pattern = req_body.caller_pattern
        callee_pattern = req_body.callee_pattern
        caller_replacement = req_body.caller_replacement
        callee_replacement = req_body.callee_replacement
        key = f'class:translation:{uuid}'
        if not rdbconn.exists(key): 
            response.status_code, result = 400, {'error': 'nonexistent_class'}; return
        rdbconn.hmset(key, {'name': name, 'desc': desc, 'caller_pattern': caller_pattern, 'callee_pattern': callee_pattern, 
                            'caller_replacement': caller_replacement, 'callee_replacement': callee_replacement})
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=update_translation_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.delete("/class/translation/{uuid}", status_code=200)
def delete_translation_class(uuid: str, response: Response):
    result = None
    try:
        if rdbconn.scard(f'engagement:translation:{uuid}'): 
            response.status_code, result = 403, {'error': 'enageged_class'}; return
        classkey = f'class:translation:{uuid}'
        if not rdbconn.exists(classkey): 
            response.status_code, result = 400, {'error': 'nonexistent_class'}; return
        rdbconn.delete(classkey)
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=delete_translation_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/class/translation/{uuid}", status_code=200)
def detail_translation_class(uuid: str, response: Response):
    result = None
    try:
        classkey = f'class:translation:{uuid}'
        if not rdbconn.exists(classkey): 
            response.status_code, result = 400, {'error': 'nonexistent_class'}; return
        data = rdbconn.hgetall(classkey)
        engagements = rembytes(rdbconn.smembers(f'engagement:translation:{uuid}'))
        data.update({'engagements': engagements})
        response.status_code, result = 200, data
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=detail_translation_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/class/translation", status_code=200)
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
                uuid = mainkey.decode().split(':')[-1]
                detail.update({'uuid': uuid})
                data.append(detail)

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
    codec: str = Field(description='uuid of codec class')
    capacity: str = Field(description='uuid of capacity class')
    translations: List[str] = Field(description='a set of translation class')
    manipualtions: List[str] = Field(description='a set of manipualtions class')

    @validator('codec')
    def check_codec_existent(cls, uuid):
        if not rdbconn.exists(f'class:codec:{uuid}'):
            raise ValueError('nonexistent_class')
        return uuid

    @validator('capacity')
    def check_capacity_existent(cls, uuid):
        if not rdbconn.exists(f'class:capacity:{uuid}'):
            raise ValueError('nonexistent_class')
        return uuid

    @root_validator('manipualtions')
    def check_manipualtion_existent(cls, uuids):
        for uuid in uuids:
            if not rdbconn.exists(f'class:manipualtion:{uuid}'):
                raise ValueError('nonexistent_class')
            return uuid

    @root_validator('translations')
    def check_translation_existent(cls, uuids):
        for uuid in uuids:
            if not rdbconn.exists(f'class:translation:{uuid}'):
                raise ValueError('nonexistent_class')
            return uuids

class InboundInterconnection(BaseModel):
    name: str = Field(regex=_NAME_, max_length=32, description='name of inbound interconnection class')
    desc: str = Field(max_length=64, description='description')
    sipprofile: str = Field(description='a sip profile uuid that interconnection engage to')
    accesses: List[IPv4Address] = Field(description='a set of signalling that use for SIP')
    medias: List[IPv4Network] = Field(description='a set of IPv4 Network that use for RTP')
    clases: ClassModel = Field(description='an object of class include codec, capacity, translations, manipualtions')
    nodes: List[str] = Field(default=['_all_'], description='a set of node member that interconnection engage to')
    enable: bool = Field(default=['true'], description='enable/disable this interconnection')


    @validator('sipprofile')
    def check_sipprofile(cls, uuid):
        if not rdbconn.exists(f'sipprofile:{uuid}'):
            raise ValueError('nonexistent_sipprofile')
        return uuid

    @validator('nodes')
    def check_node(cls, nodes):
        for node in nodes:
            if node != '_all_' and node not in CLUSTERMEMBERS:
                raise ValueError('nonexistent_sipprofile')
        return nodes

    @validator('accesses')
    def check_accesses(cls, accesses):
        for ip in accesses:
            if not rdbconn.exists(f'recognition:{sipprofile}:{ip}'):
                raise ValueError('not_unique_ip')
        return nodes


@librerouter.delete("/interconnection/inbound", status_code=200)
def create_inbound_interconnection(req_body: InboundInterconnection, response: Response):
    result = None
    try:
        name = req_body.name
        desc = req_body.desc
        caller_pattern = req_body.caller_pattern
        callee_pattern = req_body.callee_pattern
        caller_replacement = req_body.caller_replacement
        callee_replacement = req_body.callee_replacement
        uuid = guid()
        key = f'interconnection:{uuid}'
        if rdbconn.exists(key): 
            response.status_code, result = 400, {'error': 'existent_class'}; return
        rdbconn.hmset(key, {'name': name, 'desc': desc, 'caller_pattern': caller_pattern, 'callee_pattern': callee_pattern, 
                            'caller_replacement': caller_replacement, 'callee_replacement': callee_replacement})
        response.status_code, result = 200, {'uuid': uuid}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_translation_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
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
    transport: TransportEnum = Field(default='UDP', description='farend transport protocol')
    weight: int
    username: str
    password: str
    realm: str
    reigister: bool
    cid_type: str
    ping: int
    ping_max: int
    ping_min: int

class OutboundConnection(BaseModel):
    name: str
    desc: str
    sipprofile: str
    distribution: DistributionEnum
    gateways: List[GatewayModel]
    medias: List[IPv4Network]
    clases: ClassModel
    nodes: List[str]
    state: bool
