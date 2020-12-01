import traceback
import re

import redis
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from ipaddress import IPv4Address, IPv4Network
from fastapi import APIRouter, Request, Response

from configuration import (_APPLICATION, _SWVERSION, _DESCRIPTION, NODENAME, CLUSTERNAME, CLUSTER_MEMBERS,
                           SWCODECS,
                           REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD, SCAN_COUNT)
from utilities import logger, get_request_uuid, int2bool, bool2int, rembytes


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

class CodecModel(BaseModel):
    name: str = Field(regex=_NAME_, description='name of codec class')
    desc: str = Field(max_length=60, description='description')
    data: List[str] = Field(min_items=1, max_item=len(SWCODECS), description='sorted set of codec')


@librerouter.post("/class/codec", status_code=200)
def create_codec_class(req_body: CodecModel, response: Response):
    result, tracings = None, dict()
    try:
        name = req_body.name
        desc = req_body.desc
        data = req_body.data

        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        tracings['error'] = {'exception': e, 'traceback': traceback.format_exc()}
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

