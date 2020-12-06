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
from utilities import logify, debugy, get_request_uuid, int2bool, bool2int, rembytes, guid


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
    NODENAME = rembytes(rdbconn.get(f'cluster:node:{NODEID}'))
    CLUSTERNAME = rembytes(rdbconn.get('cluster:name'))
    CLUSTERMEMBERS = rembytes(rdbconn.smembers('cluster:members'))
except:
    NODENAME = _DEFAULT_NODENAME
    CLUSTERNAME = _DEFAULT_CLUSTERNAME
    CLUSTERMEMBERS = [NODEID]

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# PREDEFINED INFORMATION
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
# FUNDAMENTAL: CLUSTER NAME, NODE MEMBER
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
class ClusterModel(BaseModel):
    name: str = Field(regex=_NAME_, max_length=32, description='the name of libresbc cluster')
    members: List[str] = Field(min_items=1, max_item=10, description='the name of libresbc cluster')

    @validator('member')
    def check_member(cls, members):
        for nodeid in members:
            if not rdbconn.exists(f'cluster:node:{nodeid}'):
                raise ValueError('nonexistent_node')
        return members

@librerouter.put("/cluster/name", status_code=200)
def change_cluster_name(reqbody: ClusterModel, response: Response):
    result = None
    try:
        name = reqbody.name
        members = reqbody.members
        for member in members: pipe.sadd('cluster:members', member)
        pipe.set('cluster:name', name)
        pipe.execute()
        CLUSTERNAME, CLUSTERMEMBERS = name, members
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=change_cluster_name, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result
#--------------------------------------------------------------------------------------------
class NodeModel(BaseModel):
    id: str = Field(max_length=32, description='the name node unique-id member in libresbc cluster')
    name: Optional[str] = Field(default=_DEFAULT_NODENAME,regex=_NAME_, max_length=32, description='the name node name member in libresbc cluster')

@librerouter.post("/cluster/node", status_code=200)
def add_node(reqbody: NodeModel, response: Response):
    result = None
    try:
        id = reqbody.id
        name = reqbody.name
        rdbconn.set('cluster:node:{id}', name)
        CLUSTERNAME = name
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=add_node, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.delete("/cluster/node", status_code=200)
def delete_node(reqbody: NodeModel, response: Response):
    result = None
    try:
        id = reqbody.id
        if rdbconn.sismember('cluster:members', id):
            response.status_code, result = 403, {'error': 'node_is_a_cluster_member'}; return
        if rdbconn.scard('engagement:node:{id}'):
            response.status_code, result = 403, {'error': 'engaged_node'}; return
        key = f'cluster:node:{id}'
        if not rdbconn.exists(key): 
            response.status_code, result = 400, {'error': 'nonexistent_node'}; return
        rdbconn.delete(key)
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=delete_node, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/cluster/node/{nodeid}", status_code=200)
def detail_node(nodeid: str, response: Response):
    result = None
    try:
        key = f'cluster:node:{nodeid}'
        if not rdbconn.exists(key): 
            response.status_code, result = 400, {'error': 'nonexistent_node'}; return
        name = rdbconn.get(key)
        clustered = True if rdbconn.sismember('cluster:members', nodeid) else False
        engagements = set(rdbconn.smembers('engagement:node:{nodeid}') + rdbconn.smembers('engagement:node:_ALL_'))
        response.status_code, result = 200, {'id': id, 'name': name, 'clustered': clustered, 'engagements': engagements}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=detail_node, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/cluster/node", status_code=200)
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
            id = mainkey.decode().split(':')[-1]
            data.append({'id': id, 'name': name})

        response.status_code, result = 200, data
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=list_node, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
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


@librerouter.post("/class/codec", status_code=200)
def create_codec_class(reqbody: CodecModel, response: Response):
    result = None
    try:
        name = reqbody.name
        desc = reqbody.desc
        data = reqbody.data
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
def update_codec_class(reqbody: CodecModel, uuid: str, response: Response):
    result = None
    try:
        name = reqbody.name
        desc = reqbody.desc
        data = reqbody.data
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
def create_capacity_class(reqbody: CapacityModel, response: Response):
    result = None
    try:
        name = reqbody.name
        desc = reqbody.desc
        cps = reqbody.cps
        capacity = reqbody.capacity
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
def update_capacity_class(reqbody: CapacityModel, uuid: str, response: Response):
    result = None
    try:
        name = reqbody.name
        desc = reqbody.desc
        cps = reqbody.cps
        capacity = reqbody.capacity
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
def create_translation_class(reqbody: TranslationModel, response: Response):
    result = None
    try:
        name = reqbody.name
        desc = reqbody.desc
        caller_pattern = reqbody.caller_pattern
        callee_pattern = reqbody.callee_pattern
        caller_replacement = reqbody.caller_replacement
        callee_replacement = reqbody.callee_replacement
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
def update_translation_class(reqbody: TranslationModel, uuid: str, response: Response):
    result = None
    try:
        name = reqbody.name
        desc = reqbody.desc
        caller_pattern = reqbody.caller_pattern
        callee_pattern = reqbody.callee_pattern
        caller_replacement = reqbody.caller_replacement
        callee_replacement = reqbody.callee_replacement
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
    translations: List[str] = Field(default=[], min_items=0, max_item=5, description='a set of translation class')
    manipualtions: List[str] = Field(default=[], min_items=0, max_item=5, description='a set of manipualtions class')

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
    accesses: List[IPv4Address] = Field(min_items=1, max_item=10, description='a set of signalling that use for SIP')
    medias: List[IPv4Network] = Field(min_items=1, max_item=20, description='a set of IPv4 Network that use for RTP')
    classes: ClassModel = Field(description='an object of class include codec, capacity, translations, manipualtions')
    nodes: List[str] = Field(default=['_ALL_'], min_items=1, max_item=len(CLUSTERMEMBERS), description='a set of node member that interconnection engage to')
    enable: bool = Field(default=True, description='enable/disable this interconnection')


    @validator('sipprofile')
    def check_sipprofile(cls, uuid):
        if not rdbconn.exists(f'sipprofile:{uuid}'):
            raise ValueError('nonexistent_sipprofile')
        return uuid

    @validator('nodes')
    def check_node(cls, nodes):
        for node in nodes:
            if node != '_ALL_' and node not in CLUSTERMEMBERS:
                raise ValueError('nonexistent_node')
        return nodes


@librerouter.post("/interconnection/inbound", status_code=200)
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
        manipualtions = reqbody.classes.manipualtions
        nodes = reqbody.nodes
        enable = reqbody.enable
        uuid = guid()

        for access in accesses:
            if rdbconn.exists(f'recognition:{sipprofile}:{str(access)}'):
                response.status_code, result = 403, {'error': 'nonunique_ip_access'}; return

        pipe.hmset(f'interconnection:{uuid}:attribute', {'name': name, 'desc': desc, 'direction': 'inbound', 'sipprofile': sipprofile, nodes: json.dumps(nodes), 'enable': bool2int(enable)})
        for node in nodes: pipe.sadd(f'engagement:node:{node}', uuid)
        pipe.sadd(f'engagement:sipprofile:{sipprofile}', uuid)

        pipe.hmset(f'interconnection:{uuid}:classes', {'codec': codec, 'capacity': capacity, 'translations': json.dumps(translations), 'manipualtions': json.dumps(manipualtions)})
        pipe.sadd(f'engagement:codec:{codec}', uuid)
        pipe.sadd(f'engagement:capacity:{capacity}', uuid)
        for translation in translations: pipe.sadd(f'engagement:translation:{translation}', uuid)
        for manipualtion in manipualtions: pipe.sadd(f'engagement:manipualtion:{manipualtion}', uuid)

        for access in accesses:
            ip = str(access)
            pipe.sadd(f'interconnection:{uuid}:accesses', ip)
            pipe.set(f'recognition:{sipprofile}:{ip}', uuid)
        for media in medias:
            pipe.sadd(f'interconnection:{uuid}:medias', str(media))
        pipe.execute()
        response.status_code, result = 200, {'uuid': uuid}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_inbound_interconnection, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


@librerouter.delete("/interconnection/inbound/{uuid}", status_code=200)
def delete_inbound_interconnection(uuid: str, response: Response):
    result = None
    try:
        if not rdbconn.exists(f'interconnection:{uuid}:attribute'):
            response.status_code, result = 403, {'error': 'nonexistent_interconnection'}; return

        sipprofile = rdbconn.hget(f'interconnection:{uuid}:attribute', 'sipprofile')
        pipe.srem(f'engagement:sipprofile:{sipprofile}', uuid)
        nodes = json.loads(rdbconn.hget(f'interconnection:{uuid}:attribute', 'nodes'))
        for node in nodes: pipe.srem(f'engagement:node:{node}', uuid)
        pipe.delete(f'interconnection:{uuid}:attribute')

        codec = rdbconn.hset(f'interconnection:{uuid}:classes', 'codec')
        pipe.srem(f'engagement:codec:{codec}', uuid)
        capacity = rdbconn.hset(f'interconnection:{uuid}:classes', 'capacity')
        pipe.srem(f'engagement:capacity:{capacity}', uuid)
        translations = json.loads(rdbconn.hget(f'interconnection:{uuid}:classes', 'translations'))
        for translation in translations: pipe.srem(f'engagement:translation:{translation}', uuid)
        manipualtions = json.loads(rdbconn.hget(f'interconnection:{uuid}:classes', 'manipualtions'))
        for manipualtion in manipualtions: pipe.srem(f'engagement:manipualtion:{manipualtion}', uuid)
        pipe.delete(f'interconnection:{uuid}:classes')

        accesses = rembytes(rdbconn.smembers(f'interconnection:{uuid}:accesses'))
        for access in accesses:
            ip = str(access)
            pipe.delete(f'recognition:{sipprofile}:{ip}')
            pipe.srem(f'interconnection:{uuid}:accesses', ip)
        pipe.delete(f'interconnection:{uuid}:medias')
        pipe.execute()

        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=delete_inbound_interconnection, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.update("/interconnection/inbound/{uuid}", status_code=200)
def update_inbound_interconnection(reqbody: InboundInterconnection, uuid: str, response: Response):
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
        manipualtions = reqbody.classes.manipualtions
        nodes = reqbody.nodes
        enable = reqbody.enable

        if not rdbconn.exists(f'interconnection:{uuid}:attribute'):
            response.status_code, result = 400, {'error': 'nonexistent_interconnection'}; return

        for access in accesses:
            tmpuuid = rdbconn.exists(f'recognition:{sipprofile}:{str(access)}')
            if tmpuuid and tmpuuid!=uuid:
                response.status_code, result = 403, {'error': 'nonunique_ip_access'}; return

        _sipprofile = rdbconn.hget(f'interconnection:{uuid}:attribute', 'sipprofile')
        pipe.srem(f'engagement:sipprofile:{_sipprofile}', uuid)
        _nodes = json.loads(rdbconn.hget(f'interconnection:{uuid}:attribute', 'nodes'))
        for _node in _nodes: pipe.srem(f'engagement:node:{_node}', uuid)
        pipe.hmset(f'interconnection:{uuid}:attribute', {'name': name, 'desc': desc, 'sipprofile': sipprofile, nodes: json.dumps(nodes), 'enable': bool2int(enable)})
        for node in nodes: pipe.sadd(f'engagement:node:{node}', uuid)
        pipe.sadd(f'engagement:sipprofile:{sipprofile}', uuid)

        codec = rdbconn.hset(f'interconnection:{uuid}:classes', 'codec')
        pipe.srem(f'engagement:codec:{codec}', uuid)
        capacity = rdbconn.hset(f'interconnection:{uuid}:classes', 'capacity')
        pipe.srem(f'engagement:capacity:{capacity}', uuid)
        translations = json.loads(rdbconn.hget(f'interconnection:{uuid}:classes', 'translations'))
        for translation in translations: pipe.srem(f'engagement:translation:{translation}', uuid)
        manipualtions = json.loads(rdbconn.hget(f'interconnection:{uuid}:classes', 'manipualtions'))
        for manipualtion in manipualtions: pipe.srem(f'engagement:manipualtion:{manipualtion}', uuid)
        pipe.hmset(f'interconnection:{uuid}:classes', {'codec': codec, 'capacity': capacity, 'translations': json.dumps(translations), 'manipualtions': json.dumps(manipualtions)})
        pipe.sadd(f'engagement:codec:{codec}', uuid)
        pipe.sadd(f'engagement:capacity:{capacity}', uuid)
        for translation in translations: pipe.sadd(f'engagement:translation:{translation}', uuid)
        for manipualtion in manipualtions: pipe.sadd(f'engagement:manipualtion:{manipualtion}', uuid)

        _accesses = rembytes(rdbconn.smembers(f'interconnection:{uuid}:accesses'))
        for _access in _accesses:
            ip = str(access)
            pipe.delete(f'recognition:{sipprofile}:{ip}')
            pipe.srem(f'interconnection:{uuid}:accesses', ip)
        for access in accesses:
            ip = str(access)
            pipe.sadd(f'interconnection:{uuid}:accesses', ip)
            pipe.set(f'recognition:{sipprofile}:{ip}', uuid)
        pipe.delete(f'interconnection:{uuid}:medias')
        for media in medias:
            pipe.sadd(f'interconnection:{uuid}:medias', str(media))
        pipe.execute()
        response.status_code, result = 200, {'uuid': uuid}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_inbound_interconnection, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
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
