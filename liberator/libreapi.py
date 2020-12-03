import traceback
import re
import json

import redis
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Set
from enum import Enum
from ipaddress import IPv4Address, IPv4Network
from fastapi import APIRouter, Request, Response

from configuration import (_APPLICATION, _SWVERSION, _DESCRIPTION, NODENAME, CLUSTERNAME, CLUSTER_MEMBERS,
                           SWCODECS,
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


@librerouter.get("/predefine", status_code=200)
def predefine():
    return {
        "nodename": NODENAME,
        "cluster": CLUSTERNAME,
        "application": _APPLICATION,
        'swversion': _SWVERSION,
        "description": _DESCRIPTION
    }

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
        key = f'class:codec:{guid()}'
        if rdbconn.exists(key): 
            response.status_code, result = 400, {'error': 'existing_codec_class'}; return
        rdbconn.hmset(key, {'name': name, 'desc': desc, 'data': json.dumps(data)})
        response.status_code, result = 200, {'id': id}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_codec_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.put("/class/codec/{id}", status_code=200)
def update_codec_class(req_body: CodecModel, id: str, response: Response):
    result = None
    try:
        name = req_body.name
        desc = req_body.desc
        data = req_body.data
        key = f'class:codec:{id}'
        if not rdbconn.exists(key): 
            response.status_code, result = 400, {'error': 'no_existing_codec_class'}; return
        rdbconn.hmset(key, {'desc': desc, 'data': json.dumps(data)})
        response.status_code, result = 200, {'id': id}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=update_codec_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.delete("/class/codec/{id}", status_code=200)
def delete_codec_class(id: str, response: Response):
    result = None
    try:
        if rdbconn.scard(f'engagement:codec:{id}'): 
            response.status_code, result = 403, {'error': 'enageged_class'}; return
        classkey = f'class:codec:{id}'
        if not rdbconn.exists(classkey): 
            response.status_code, result = 400, {'error': 'no_existing_codec_class'}; return
        rdbconn.delete(classkey)
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=delete_codec_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/class/codec/{id}", status_code=200)
def detail_codec_class(id: str, response: Response):
    result = None
    try:
        classkey = f'class:codec:{id}'
        if not rdbconn.exists(classkey): 
            response.status_code, result = 400, {'error': 'no_existing_codec_class'}; return
        data = rdbconn.hgetall(classkey)
        engaged_keys = rembytes(rdbconn.smembers(f'engagement:codec:{id}'))
        for engaged_key in engaged_keys:
            pipe.hget(engaged_key, 'name')
        data.update({'engements': pipe.execute()})
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
                id = mainkey.decode().split(':')[-1]
                detail.update({'id': id})
                data.append(detail)

        response.status_code, result = 200, data
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=list_codec_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result




class SecureProtocol(BaseModel):
    tls: List[str]
    srtp: List[str]
    cipher: List[str]

class CapacityModel(BaseModel):
    name: str
    desc: str
    cps: int
    capacity: int

class TranslationModel(BaseModel):
    name: str
    desc: str
    caller_pattern: str
    callee_pattern: str
    caller_replacement: str
    callee_replacement: str

class GatewayModel(BaseModel):
    ip: IPv4Address
    port: int
    transport: str
    weight: int
    username: str
    password: str
    realm: str
    reigister: bool
    cid_type: str
    ping: int
    ping_max: int
    ping_min: int

class DistributionModel(BaseModel):
    gateways: List[GatewayModel]
    mechanism: str
    # round-robin, weight, hash caller/callee

class ClassModel(BaseModel):
    codec: str
    capacity: str
    translations: List[str]
    manipualtions: List[str]

class OutboundConnection(BaseModel):
    name: str
    desc: str
    sipprofile: str
    distribution: List[DistributionModel] 
    medias: List[IPv4Network]
    clases: ClassModel
    nodes: List[str]
    state: bool

class InboundConnection(BaseModel):
    name: str
    desc: str
    sipprofile: str
    signallings: List[IPv4Address] 
    medias: List[IPv4Network]
    clases: ClassModel
    nodes: List[str]
    state: bool

