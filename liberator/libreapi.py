#
# liberator:libreapi.py
#
# The Initial Developer of the Original Code is
# Minh Minh <hnimminh at[@] outlook dot[.] com>
# Portions created by the Initial Developer are Copyright (C) the Initial Developer.
# All Rights Reserved.
#

import traceback
import re
import json
import hashlib

import redis
import validators
from pydantic import BaseModel, Field, validator, root_validator, schema
from pydantic.fields import ModelField
from typing import Optional, List, Dict, Union, Any
from enum import Enum
from ipaddress import IPv4Address, IPv4Network
from fastapi import APIRouter, Request, Response, Path
from fastapi.encoders import jsonable_encoder

from configuration import (_APPLICATION, _SWVERSION, _DESCRIPTION, CHANGE_CFG_CHANNEL, SECURITY_CHANNEL,
                           NODEID, SWCODECS, CLUSTERS, _BUILTIN_ACLS_,
                           REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD, SCAN_COUNT)
from utilities import logify, debugy, get_request_uuid, int2bool, bool2int, redishash, jsonhash, fieldjsonify, fieldredisify, listify, stringify, getaname, removekey


REDIS_CONNECTION_POOL = redis.BlockingConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD,
                                                     decode_responses=True, max_connections=10, timeout=5)
rdbconn = redis.StrictRedis(connection_pool=REDIS_CONNECTION_POOL)


# API ROUTER DECLARATION
librerouter = APIRouter()

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# PYDANTIC SCHEME HIDE FIELD
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
def field_schema(field: ModelField, **kwargs: Any) -> Any:
    if field.field_info.extra.get("hidden_field", False):
        raise schema.SkipField(f"{field.name} field is being hidden with fastapi/issues/1378")
    else:
        return original_field_schema(field, **kwargs)

original_field_schema = schema.field_schema
schema.field_schema = field_schema

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# CONSTANTS
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# PATTERN
_NAME_ = r'^[a-zA-Z][a-zA-Z0-9_]+$'
_SRNAME_ = r'^_[a-zA-Z0-9_]+$'
_REALM_ = r'^[a-z][a-z0-9_\-\.]+$'
_DIAL_ = r'^[a-zA-Z0-9_\-+#*@]*$'
# ROUTING
_QUERY = 'query'
_BLOCK = 'block'
_JUMPS = 'jumps'
_ROUTE = 'route'
# reserved for value empty string
__DEFAULT_ENTRY__ = '__DEFAULT_ENTRY__'
__EMPTY_STRING__ = ''
__COLON__ = ':'
__COMMA__ = ','
__SEMICOLON__ = ';'
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# INITIALIZE
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------

try:
    rdbconn.sadd('cluster:candidates', NODEID)

    _clustername = rdbconn.get('cluster:name')
    if _clustername: CLUSTERS['name'] = _clustername
    _clustermembers = set(rdbconn.smembers('cluster:members'))
    if _clustermembers: CLUSTERS['members'] = list(_clustermembers)

    attributes = jsonhash(rdbconn.hgetall('cluster:attributes'))
    _rtp_start_port = attributes.get('rtp_start_port')
    if _rtp_start_port: CLUSTERS['rtp_start_port'] = _rtp_start_port
    _rtp_end_port = attributes.get('rtp_end_port')
    if _rtp_end_port: CLUSTERS['rtp_end_port'] = _rtp_end_port
    _max_concurrent_calls = attributes.get('max_concurrent_calls')
    if _max_concurrent_calls: CLUSTERS['max_concurrent_calls'] = _max_concurrent_calls
    _max_calls_per_second = attributes.get('max_calls_per_second')
    if _max_calls_per_second: CLUSTERS['max_calls_per_second'] = _max_calls_per_second
except Exception as e:
    logify(f"module=liberator, space=libreapi, action=initiate, exception={e}, traceback={traceback.format_exc()}")

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# PREDEFINED INFORMATION
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
@librerouter.get("/libreapi/predefine", status_code=200)
def predefine():
    return {
        'application': _APPLICATION,
        'swversion': _SWVERSION,
        'description': _DESCRIPTION,
        'nodeid': NODEID,
        'candidates': rdbconn.smembers('cluster:candidates'),
        #'cluster': CLUSTERS,
        'codecs': SWCODECS,
    }

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# CLUSTER & NODE
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------

def check_member(members):
    for member in members:
        if not rdbconn.sismember('cluster:candidates', member):
            raise ValueError('member is not in candidates')
    return members

class ClusterModel(BaseModel):
    name: str = Field(regex=_NAME_, max_length=32, description='The name of libresbc cluster')
    members: List[str] = Field(min_items=1, max_item=16, description='The member of libresbc cluster')
    rtp_start_port: int = Field(default=10000, min=0, max=65535, description='start of rtp port range')
    rtp_end_port: int = Field(default=60000, min=0, max=65535, description='start of rtp port range')
    max_concurrent_calls: int = Field(default=6000, min=0, max=65535, description='maximun number of active (concurent) call that one cluster member can handle')
    max_calls_per_second: int = Field(default=200, min=0, max=65535, description='maximun number of calls attempt in one second that one cluster member can handle')
    # validation
    _validmember = validator('members')(check_member)


@librerouter.put("/libreapi/cluster", status_code=200)
def update_cluster(reqbody: ClusterModel, response: Response):
    result = None
    requestid=get_request_uuid()
    try:
        pipe = rdbconn.pipeline()
        name = reqbody.name
        members = set(reqbody.members)
        rtp_start_port = reqbody.rtp_start_port
        rtp_end_port = reqbody.rtp_end_port
        max_concurrent_calls = reqbody.max_concurrent_calls
        max_calls_per_second = reqbody.max_calls_per_second
        _members = set(rdbconn.smembers('cluster:members'))
        removed_members = _members - members
        for removed_member in removed_members:
            if rdbconn.scard(f'engagement:node:{removed_member}'):
                response.status_code, result = 403, {'error': 'engaged node'}; return

        pipe.set('cluster:name', name)
        for member in members: pipe.sadd('cluster:members', member)
        pipe.hmset('cluster:attributes', redishash({'rtp_start_port': rtp_start_port, 'rtp_end_port': rtp_end_port, 'max_concurrent_calls': max_concurrent_calls, 'max_calls_per_second': max_calls_per_second}))
        pipe.execute()
        CLUSTERS.update({
            'name': name,
            'members': list(members),
            'rtp_start_port': rtp_start_port,
            'rtp_end_port': rtp_end_port,
            'max_concurrent_calls': max_concurrent_calls,
            'max_calls_per_second': max_calls_per_second
        })
        # fire-event cluster member to fsvar
        rdbconn.publish(CHANGE_CFG_CHANNEL, json.dumps({'portion': 'cluster', 'action': 'update', 'fsgvars': [f'CLUSTERMEMBERS={stringify(members,__COMMA__)}'], 'requestid': requestid}))
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=change_cluster, requestid={requestid}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


@librerouter.get("/libreapi/cluster", status_code=200)
def get_cluster(response: Response):
    result = None
    try:
        response.status_code, result = 200, CLUSTERS
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=get_cluster, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result



#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# NETWORK ALIAS
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------

def netalias_agreement(addresses):
    _addresses = jsonable_encoder(addresses)
    if len(_addresses) != len(CLUSTERS.get('members')):
        raise ValueError('The alias must be set for only/all cluster members')
    for address in _addresses:
        member = address['member']
        if not rdbconn.sismember('cluster:candidates', member):
            raise ValueError(f'{member} is invalid candidates')
    return addresses

class IPSuite(BaseModel):
    member: str = Field(regex=_NAME_, description='NodeID of member in cluster')
    listen: IPv4Address = Field(description='the listen ip address')
    advertise: IPv4Address = Field(description='the advertising ip address')

class NetworkAlias(BaseModel):
    name: str = Field(regex=_NAME_, max_length=32, description='name of network alias (identifier)')
    desc: Optional[str] = Field(default='', max_length=64, description='description')
    addresses: List[IPSuite] = Field(description='List of IP address suite for cluster members')
    # validation
    _validnetalias = validator('addresses')(netalias_agreement)


@librerouter.post("/libreapi/base/netalias", status_code=200)
def create_netalias(reqbody: NetworkAlias, response: Response):
    requestid=get_request_uuid()
    result = None
    try:
        pipe = rdbconn.pipeline()
        name = reqbody.name
        name_key = f'base:netalias:{name}'
        if rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent network alias name'}; return
        data = jsonable_encoder(reqbody)
        pipe.hmset(name_key, redishash(data))
        pipe.sadd(f'nameset:netalias', name)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_netalias, requestid={requestid}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.put("/libreapi/base/netalias/{identifier}", status_code=200)
def update_netalias(reqbody: NetworkAlias, response: Response, identifier: str=Path(..., regex=_NAME_)):
    requestid=get_request_uuid()
    result = None
    try:
        pipe = rdbconn.pipeline()
        name = reqbody.name
        _name_key = f'base:netalias:{identifier}'
        name_key = f'base:netalias:{name}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent network alias identifier'}; return
        if name != identifier and rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent network alias name'}; return
        data = jsonable_encoder(reqbody)
        rdbconn.hmset(name_key, redishash(data))
        # proactive get list who use this netalias
        _engaged_key = f'engagement:{_name_key}'
        engaged_key = f'engagement:{name_key}'
        engagements = rdbconn.smembers(_engaged_key)
        if name != identifier:
            for engagement in engagements:
                if rdbconn.hget(engagement, 'rtp_address') == identifier:
                    pipe.hset(engagement, 'rtp_address', name)
                if rdbconn.hget(engagement, 'sip_address') == identifier:
                    pipe.hset(engagement, 'sip_address', name)
            if rdbconn.exists(_engaged_key):
                pipe.rename(_engaged_key, engaged_key)
            pipe.delete(_name_key)
            pipe.srem(f'nameset:netalias', identifier)
            pipe.sadd(f'nameset:netalias', name)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
        # fire-event netalias change, process reload only if there is some-one use it
        if engagements:
            sipprofiles = [getaname(engagement) for engagement in engagements]
            rdbconn.publish(CHANGE_CFG_CHANNEL, json.dumps({'portion': 'netalias', 'sipprofiles': sipprofiles, 'requestid': requestid}))
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=update_netalias, requestid={requestid}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.delete("/libreapi/base/netalias/{identifier}", status_code=200)
def delete_netalias(response: Response, identifier: str=Path(..., regex=_NAME_)):
    requestid=get_request_uuid()
    result = None
    try:
        pipe = rdbconn.pipeline()
        _name_key = f'base:netalias:{identifier}'
        _engage_key = f'engagement:{_name_key}'
        if rdbconn.scard(_engage_key):
            response.status_code, result = 403, {'error': 'engaged network alias'}; return
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent network alias identifier'}; return
        pipe.delete(_engage_key)
        pipe.delete(_name_key)
        pipe.srem(f'nameset:netalias', identifier)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
        # delete action perform only no one use it so no-one use mean no need reload as this not loaded to memory
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=delete_acl, requestid={requestid}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libreapi/base/netalias/{identifier}", status_code=200)
def detail_netalias(response: Response, identifier: str=Path(..., regex=_NAME_)):
    result = None
    try:
        _name_key = f'base:netalias:{identifier}'
        _engage_key = f'engagement:{_name_key}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent network alias identifier'}; return
        result = jsonhash(rdbconn.hgetall(_name_key))
        engagements = rdbconn.smembers(_engage_key)
        result.update({'engagements': engagements})
        response.status_code = 200
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=detail_netalias, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libreapi/base/netalias", status_code=200)
def list_netalias(response: Response):
    result = None
    try:
        pipe = rdbconn.pipeline()
        KEYPATTERN = f'base:netalias:*'
        next, mainkeys = rdbconn.scan(0, KEYPATTERN, SCAN_COUNT)
        while next:
            next, tmpkeys = rdbconn.scan(next, KEYPATTERN, SCAN_COUNT)
            mainkeys += tmpkeys

        for mainkey in mainkeys:
            pipe.hget(mainkey, 'desc')
        descs = pipe.execute()
        data = [{'name': getaname(mainkey), 'desc': desc} for mainkey, desc in zip(mainkeys, descs)]
        response.status_code, result = 200, data
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=list_netalias, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# SYSTEMWIDE FIREWALL IP WHITE/BLACK
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
@librerouter.patch("/libreapi/base/firewall/{nameset}", status_code=200)
def update_fwset(reqbody: List[IPv4Address], response: Response, nameset: str=Path(..., regex='^whiteset|blackset$')):
    requestid=get_request_uuid()
    result = None
    try:
        pipe = rdbconn.pipeline()
        name_key = f'firewall:{nameset}'
        ipaddrs = jsonable_encoder(reqbody)
        _ipaddrs = rdbconn.smembers(name_key)

        remlist = list(set(_ipaddrs) - set(ipaddrs))
        addlist = list(set(ipaddrs) - set(_ipaddrs))
        for ipaddr in remlist:
            pipe.srem(name_key, ipaddr)
        for ipaddr in addlist:
            pipe.sadd(name_key, ipaddr)
        pipe.execute()
        if remlist: rdbconn.publish(SECURITY_CHANNEL, json.dumps({'portion': f'api:{nameset}', 'srcips': remlist, '_flag': True}))
        if addlist: rdbconn.publish(SECURITY_CHANNEL, json.dumps({'portion': f'api:{nameset}', 'srcips': addlist}))
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=update_fwset, requestid={requestid}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libreapi/base/firewall", status_code=200)
def get_fwset(response: Response):
    result = None
    try:
        whiteset = list(rdbconn.smembers('firewall:whiteset'))
        blackset = list(rdbconn.smembers('firewall:blackset'))
        result = {'whiteset': whiteset, 'blackset': blackset}
        response.status_code = 200
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=get_fwset, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ACL
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------

class ACLActionEnum(str, Enum):
    allow = 'allow'
    deny = 'deny'

class ACLTypeEnum(str, Enum):
    cidr = 'cidr'
    domain = 'domain'

class ACLRuleModel(BaseModel):
    action: ACLActionEnum = Field(default='allow', description='associate action for node')
    key: ACLTypeEnum = Field(default='cidr', description='type of acl node: cidr, domain')
    value: str = Field(description='acl rule value depend on type')
    force: Optional[bool] = Field(description='set true if you need to add acl domain', hidden_field=True)

    @root_validator()
    def acl_rule_agreement(cls, rule):
        key = rule.get('key')
        value = rule.get('value')
        if key=='cidr':
            if not IPv4Network(value):
                raise ValueError('for cidr key, value must be IPv4Network or IPv4Address')
        else:
            force = rule.get('force')
            if force:
                if not validators.domain(value): raise ValueError('for domain key, value must be domain')
            else: raise ValueError('to add domain acl, please set force=true & do at your own risk')
        rule.pop('force', None)

        return rule

class ACLModel(BaseModel):
    name: str = Field(regex=_NAME_, max_length=32, description='name of acl (identifier)')
    desc: Optional[str] = Field(default='', max_length=64, description='description')
    action: ACLActionEnum = Field(default='deny', description='default action')
    rules: List[ACLRuleModel] = Field(min_items=1, max_items=64, description='default action')


@librerouter.post("/libreapi/base/acl", status_code=200)
def create_acl(reqbody: ACLModel, response: Response):
    requestid=get_request_uuid()
    result = None
    try:
        pipe = rdbconn.pipeline()
        name = reqbody.name
        name_key = f'base:acl:{name}'
        if rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent acl name'}; return
        data = jsonable_encoder(reqbody)
        rdbconn.hmset(name_key, redishash(data))
        response.status_code, result = 200, {'passed': True}
        # fire-event acl change
        rdbconn.publish(CHANGE_CFG_CHANNEL, json.dumps({'portion': 'acl', 'requestid': requestid}))
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_acl, requestid={requestid}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.put("/libreapi/base/acl/{identifier}", status_code=200)
def update_acl(reqbody: ACLModel, response: Response, identifier: str=Path(..., regex=_NAME_)):
    requestid=get_request_uuid()
    result = None
    try:
        pipe = rdbconn.pipeline()
        name = reqbody.name
        _name_key = f'base:acl:{identifier}'
        name_key = f'base:acl:{name}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent acl identifier'}; return
        if name != identifier and rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent class name'}; return
        data = jsonable_encoder(reqbody)
        rdbconn.hmset(name_key, redishash(data))
        # proactive get list who use this acl
        _engaged_key = f'engagement:{_name_key}'
        engaged_key = f'engagement:{name_key}'
        engagements = rdbconn.smembers(_engaged_key)
        if name != identifier:
            for engagement in engagements:
                pipe.hset(engagement, 'local_network_acl', name)
            if rdbconn.exists(_engaged_key):
                pipe.rename(_engaged_key, engaged_key)
            pipe.delete(_name_key)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
        # fire-event acl change, process reload only if there is some-one use it
        if engagements:
            sipprofiles = [getaname(engagement) for engagement in engagements]
            rdbconn.publish(CHANGE_CFG_CHANNEL, json.dumps({'portion': 'acl', 'sipprofiles': sipprofiles, 'name': name, '_name': identifier, 'requestid': requestid}))
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=update_acl, requestid={requestid}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.delete("/libreapi/base/acl/{identifier}", status_code=200)
def delete_acl(response: Response, identifier: str=Path(..., regex=_NAME_)):
    requestid=get_request_uuid()
    result = None
    try:
        pipe = rdbconn.pipeline()
        #
        _name_key = f'base:acl:{identifier}'
        _engage_key = f'engagement:{_name_key}'
        if rdbconn.scard(_engage_key):
            response.status_code, result = 403, {'error': 'engaged acl'}; return
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent acl identifier'}; return
        pipe.delete(_engage_key)
        pipe.delete(_name_key)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
        # delete action perform only no one use it so no-one use it, by right this should be clean on memory
        # however best practice of optimization it will be luckily clear sometime later if acl change
        rdbconn.publish(CHANGE_CFG_CHANNEL, json.dumps({'portion': 'acl', 'requestid': requestid}))
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=delete_acl, requestid={requestid}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libreapi/base/acl/{identifier}", status_code=200)
def detail_acl(response: Response, identifier: str=Path(..., regex=_NAME_)):
    result = None
    try:
        _name_key = f'base:acl:{identifier}'
        _engage_key = f'engagement:{_name_key}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent acl identifier'}; return
        result = jsonhash(rdbconn.hgetall(_name_key))
        engagements = rdbconn.smembers(_engage_key)
        result.update({'engagements': engagements})
        response.status_code = 200
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=detail_acl, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libreapi/base/acl", status_code=200)
def list_acl(response: Response):
    result = None
    try:
        pipe = rdbconn.pipeline()
        KEYPATTERN = f'base:acl:*'
        next, mainkeys = rdbconn.scan(0, KEYPATTERN, SCAN_COUNT)
        while next:
            next, tmpkeys = rdbconn.scan(next, KEYPATTERN, SCAN_COUNT)
            mainkeys += tmpkeys

        for mainkey in mainkeys:
            pipe.hget(mainkey, 'desc')
        descs = pipe.execute()
        data = [{'name': getaname(mainkey), 'desc': desc} for mainkey, desc in zip(mainkeys, descs)]
        response.status_code, result = 200, data
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=list_acl, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# SIP PROFILES
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------

class ContextEnum(str, Enum):
    core = "core"
    carrier = "carrier"
    access = "access"

class DtmfType(str, Enum):
    rfc2833 = "rfc2833"
    info = "info"
    none = "none"

class SIPProfileModel(BaseModel):
    name: str = Field(regex=_NAME_, max_length=32, description='friendly name of sip profile')
    desc: str = Field(default='', max_length=64, description='description')
    user_agent: str = Field(default='LibreSBC', max_length=64, description='Value that will be displayed in SIP header User-Agent')
    sdp_user: str = Field(default='LibreSBC', max_length=64, description='username with the o= and s= fields in SDP body')
    local_network_acl: str = Field(default='rfc1918.auto', description='set the local network that refer from predefined acl')
    enable_100rel: bool = Field(default=True, description='Reliability - PRACK message as defined in RFC3262')
    ignore_183nosdp: bool = Field(default=True, description='Just ignore SIP 183 without SDP body')
    sip_options_respond_503_on_busy: bool = Field(default=True, description='response 503 when system is in heavy load')
    disable_transfer: bool = Field(default=False, description='true mean disable call transfer')
    manual_redirect: bool = Field(default=False, description='how call forward handled, true mean it be controlled under libresbc contraints, false mean it be work automatically')
    enable_3pcc: bool = Field(default=False, description='determines if third party call control is allowed or not')
    enable_compact_headers: bool = Field(default=False, description='disable as default, true to enable compact SIP headers')
    enable_timer: bool = Field(default=False, description='true to support for RFC 4028 SIP Session Timers')
    session_timeout: int = Field(default=0, ge=1800, le=3600, description='call to expire after the specified seconds')
    minimum_session_expires: int = Field(default=120, ge=90, le=3600, description='Value of SIP header Min-SE')
    dtmf_type: DtmfType = Field(default='rfc2833', description='Dual-tone multi-frequency (DTMF) signal type')
    media_timeout: int = Field(default=0, description='The number of seconds of RTP inactivity before SBC considers the call disconnected, and hangs up (recommend to use session timers instead), default value is 0 - disables the timeout.')
    rtp_rewrite_timestamps: bool = Field(default=False, description='set true to regenerate and rewrite the timestamps in all the RTP streams going to an endpoint using this SIP Profile, necessary to fix audio issues when sending calls to some paranoid and not RFC-compliant gateways')
    realm: Optional[str] = Field(regex=_REALM_, max_length=256, description='realm challenge key for digest auth, mainpoint to identify which directory domain that user belong to. This setting can be used with ALC (be careful to use & do at your own risk)', hidden_field=True)
    context: ContextEnum = Field(description='predefined context for call control policy')
    sip_port: int = Field(default=5060, ge=0, le=65535, description='Port to bind to for SIP traffic')
    sip_address: str = Field(description='IP address via NetAlias use for SIP Signalling')
    rtp_address: str = Field(description='IP address via NetAlias use for RTP Media')
    tls: bool = Field(default=False, description='true to enable TLS')
    tls_only: bool = Field(default=False, description='set True to disable listening on the unencrypted port for this connection')
    sips_port: int = Field(default=5061, ge=0, le=65535, description='Port to bind to for TLS SIP traffic')
    tls_version: str = Field(min_length=4, max_length=64, default='tlsv1.2', description='TLS version', hidden_field=True)
    tls_cert_dir: Optional[str] = Field(min_length=4, max_length=256, description='TLS Certificate dirrectory', hidden_field=True)
    # validation
    @root_validator()
    def sipprofile_agreement(cls, values):
        _values = jsonable_encoder(values)
        for key, value in _values.items():
            # SIP TIMER
            if key=='enable_timer' and not value :
                removekey(['enable_timer', 'session_timeout', 'minimum_session_expires'], values)
            # SIP TLS
            if key=='sip_tls' and not value :
                removekey(['sip_tls', 'sips_port', 'tls_only', 'tls_version', 'tls_cert_dir'], values)

            if key=='local_network_acl':
                if value not in _BUILTIN_ACLS_:
                    if not rdbconn.exists(f'base:acl:{value}'):
                        raise ValueError('nonexistent acl')

            if key in ['sip_address', 'rtp_address']:
                if not rdbconn.exists(f'base:netalias:{value}'):
                    raise ValueError('nonexistent network alias')

            # remove the key's value is None
            if value is None:
                 values.pop(key, None)

        # REALM
        name = values.get('name')
        realm = values.get('realm')
        if realm:
            _profile = rdbconn.srandmember(f'engagement:base:realm:{realm}')
            if _profile:
                _name = getaname(_profile)
                if _name != name: raise ValueError(f'realm is used by {_name}')
        else:
            values['realm'] = f'{name}.libresbc'

        return values


@librerouter.post("/libreapi/sipprofile", status_code=200)
def create_sipprofile(reqbody: SIPProfileModel, response: Response):
    requestid=get_request_uuid()
    result = None
    try:
        pipe = rdbconn.pipeline()
        name = reqbody.name
        data = jsonable_encoder(reqbody)
        name_key = f'sipprofile:{name}'
        if rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent sip profile name'}; return
        local_network_acl = data.get('local_network_acl')
        sip_address = data.get('sip_address')
        rtp_address = data.get('rtp_address')
        realm = data.get('realm')
        pipe.hmset(name_key, redishash(data))
        if local_network_acl not in _BUILTIN_ACLS_: pipe.sadd(f'engagement:base:acl:{local_network_acl}', name_key)
        pipe.sadd(f'engagement:base:netalias:{sip_address}', name_key)
        pipe.sadd(f'engagement:base:netalias:{rtp_address}', name_key)
        pipe.sadd(f'engagement:base:realm:{realm}', name_key)
        pipe.sadd(f'nameset:sipprofile', name)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
        # fire-event sip profile create
        rdbconn.publish(CHANGE_CFG_CHANNEL, json.dumps({'portion': 'sofiasip', 'action': 'create', 'sipprofile': name, 'requestid': requestid}))
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_sipprofile, requestid={requestid}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.put("/libreapi/sipprofile/{identifier}", status_code=200)
def update_sipprofile(reqbody: SIPProfileModel, response: Response, identifier: str=Path(..., regex=_NAME_)):
    requestid=get_request_uuid()
    result = None
    try:
        pipe = rdbconn.pipeline()
        name = reqbody.name
        _name_key = f'sipprofile:{identifier}'
        name_key = f'sipprofile:{name}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent sip profile identifier'}; return
        if name != identifier and rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent sip profile name'}; return

        _data = jsonhash(rdbconn.hgetall(_name_key))
        _local_network_acl = _data.get('local_network_acl')
        _sip_address = _data.get('sip_address')
        _rtp_address = _data.get('rtp_address')
        _realm = _data.get('realm')

        data = jsonable_encoder(reqbody)
        local_network_acl = data.get('local_network_acl')
        sip_address = data.get('sip_address')
        rtp_address = data.get('rtp_address')
        realm = _data.get('realm')
        if _local_network_acl not in _BUILTIN_ACLS_: pipe.srem(f'engagement:base:acl:{_local_network_acl}', _name_key)
        pipe.srem(f'engagement:base:netalias:{_sip_address}', _name_key)
        pipe.srem(f'engagement:base:netalias:{_rtp_address}', _name_key)
        pipe.delete(f'engagement:base:realm:{_realm}')
        if local_network_acl not in _BUILTIN_ACLS_: pipe.sadd(f'engagement:base:acl:{local_network_acl}', name_key)
        pipe.sadd(f'engagement:base:netalias:{sip_address}', name_key)
        pipe.sadd(f'engagement:base:netalias:{rtp_address}', name_key)
        pipe.sadd(f'engagement:base:realm:{realm}', name_key)
        pipe.hmset(name_key, redishash(data))
        # remove the unintended-field
        for _field in _data:
            if _field not in data:
                pipe.hdel(_name_key, _field)
        # if name is changed
        if name != identifier:
            _engaged_key = f'engagement:{_name_key}'
            engaged_key = f'engagement:{name_key}'
            engagements = rdbconn.smembers(_engaged_key)
            for engagement in engagements:
                pipe.hset(f'intcon:{engagement}', 'sipprofile', name)
            if rdbconn.exists(_engaged_key):
                pipe.rename(_engaged_key, engaged_key)
            pipe.delete(_name_key)
            pipe.srem(f'nameset:sipprofile', identifier)
            pipe.sadd(f'nameset:sipprofile', name)
            if rdbconn.exists(f'farendsipaddrs:in:{identifier}'):
                pipe.rename(f'farendsipaddrs:in:{identifier}', f'farendsipaddrs:in:{name}')
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
        # fire-event sip profile update
        rdbconn.publish(CHANGE_CFG_CHANNEL, json.dumps({'portion': 'sofiasip', 'action': 'update', 'sipprofile': name, '_sipprofile': identifier, 'requestid': requestid}))
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=update_sipprofile, requestid={requestid}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.delete("/libreapi/sipprofile/{identifier}", status_code=200)
def delete_sipprofile(response: Response, identifier: str=Path(..., regex=_NAME_)):
    requestid=get_request_uuid()
    result = None
    try:
        pipe = rdbconn.pipeline()
        _name_key = f'sipprofile:{identifier}'
        _engage_key = f'engagement:{_name_key}'
        if rdbconn.scard(_engage_key):
            response.status_code, result = 403, {'error': 'engaged sipprofile'}; return
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent sipprofile'}; return
        _local_network_acl = rdbconn.hget(_name_key, 'local_network_acl')
        _sip_address = rdbconn.hget(_name_key, 'sip_address')
        _rtp_address = rdbconn.hget(_name_key, 'rtp_address')
        _realm = rdbconn.hget(_name_key, 'realm')
        if _local_network_acl not in _BUILTIN_ACLS_: pipe.srem(f'engagement:base:acl:{_local_network_acl}', _name_key)
        pipe.srem(f'engagement:base:netalias:{_sip_address}', _name_key)
        pipe.srem(f'engagement:base:netalias:{_rtp_address}', _name_key)
        pipe.delete(f'engagement:base:realm:{_realm}')
        pipe.srem(f'nameset:sipprofile', identifier)
        pipe.delete(_engage_key)
        pipe.delete(_name_key)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
        # fire-event sip profile delete
        rdbconn.publish(CHANGE_CFG_CHANNEL, json.dumps({'portion': 'sofiasip', 'action': 'delete', '_sipprofile': identifier, 'requestid': requestid}))
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=delete_sipprofile, requestid={requestid}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libreapi/sipprofile/{identifier}", status_code=200)
def detail_sipprofile(response: Response, identifier: str=Path(..., regex=_NAME_)):
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

@librerouter.get("/libreapi/sipprofile", status_code=200)
def list_sipprofile(response: Response):
    result = None
    try:
        pipe = rdbconn.pipeline()
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
                data.append({'name': getaname(mainkey), 'desc': detail[0]})

        response.status_code, result = 200, data
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=list_sipprofile, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# PREANSWER CLASS
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------


class PreAnswerTypeEnum(str, Enum):
    tone = 'tone'
    media = 'media'
    speak = 'speak'

class PreAnswerStream(BaseModel):
    type: PreAnswerTypeEnum = Field(default='tone', description='media type: tone - tone script follow ITU-T Recommendation E.180, media - filename (fullpath) of audio file, speak - text to speak')
    stream: str = Field(min_length=8, max_length=511, description='stream data follow the media type')
    # will do validate yet in next release
    @root_validator()
    def preanswer_stream_agreement(cls, stream):
        streamtype = stream.get('type')
        streamdata = stream.get('stream')
        return stream

class PreAnswerModel(BaseModel):
    name: str = Field(regex=_NAME_, max_length=32, description='name of preanswer class (identifier)')
    desc: Optional[str] = Field(default='', max_length=64, description='description')
    streams: List[PreAnswerStream] = Field(min_items=1, max_items=8, description='List of PreAnswer Stream')

@librerouter.post("/libreapi/class/preanswer", status_code=200)
def create_preanswer_class(reqbody: PreAnswerModel, response: Response):
    result = None
    try:
        name = reqbody.name
        data = jsonable_encoder(reqbody)
        name_key = f'class:preanswer:{name}'
        if rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent class name'}; return
        rdbconn.hmset(name_key, redishash(data))
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_preanswer_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.put("/libreapi/class/preanswer/{identifier}", status_code=200)
def update_preanswer_class(reqbody: PreAnswerModel, response: Response, identifier: str=Path(..., regex=_NAME_)):
    result = None
    try:
        pipe = rdbconn.pipeline()
        name = reqbody.name
        data = jsonable_encoder(reqbody)
        _name_key = f'class:preanswer:{identifier}'
        name_key = f'class:preanswer:{name}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent class identifier'}; return
        if name != identifier and rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent class name'}; return
        rdbconn.hmset(name_key, redishash(data))
        if name != identifier:
            _engaged_key = f'engagement:{_name_key}'
            engaged_key = f'engagement:{name_key}'
            engagements = rdbconn.smembers(_engaged_key)
            for engagement in engagements:
                pipe.hset(f'intcon:{engagement}', 'preanswer_class', name)
            if rdbconn.exists(_engaged_key):
                pipe.rename(_engaged_key, engaged_key)
            pipe.delete(_name_key)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=update_preanswer_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.delete("/libreapi/class/preanswer/{identifier}", status_code=200)
def delete_preanswer_class(response: Response, identifier: str=Path(..., regex=_NAME_)):
    result = None
    try:
        pipe = rdbconn.pipeline()
        _name_key = f'class:preanswer:{identifier}'
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
        logify(f"module=liberator, space=libreapi, action=delete_preanswer_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libreapi/class/preanswer/{identifier}", status_code=200)
def detail_preanswer_class(response: Response, identifier: str=Path(..., regex=_NAME_)):
    result = None
    try:
        _name_key = f'class:preanswer:{identifier}'
        _engage_key = f'engagement:{_name_key}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent class identifier'}; return
        result = jsonhash(rdbconn.hgetall(_name_key))
        engagements = rdbconn.smembers(_engage_key)
        result.update({'engagements': engagements})
        response.status_code = 200
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=detail_preanswer_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libreapi/class/preanswer", status_code=200)
def list_preanswer_class(response: Response):
    result = None
    try:
        pipe = rdbconn.pipeline()
        KEYPATTERN = f'class:preanswer:*'
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
                data.append({'name': getaname(mainkey), 'desc': detail[0]})

        response.status_code, result = 200, data
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=list_preanswer_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# MEDIA CLASS
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
class CodecEnum(str, Enum):
    PCMA = "PCMA"
    PCMU = "PCMU"
    OPUS = "OPUS"
    G729 = "G729"
    AMR = "AMR"
    AMRWB = "AMR-WB"


class NegotiationMode(str, Enum):
    generous = 'generous'
    greedy = 'greedy'
    scrooge = 'scrooge'

class MediaModeEnum(str, Enum):
    transcode = 'transcode'
    proxy = 'proxy'
    bypass = 'bypass'

class DtmfModeEnum(str, Enum):
    rfc2833 = 'rfc2833'
    info = 'info'
    none = 'none'

class MediaModel(BaseModel):
    name: str = Field(regex=_NAME_, max_length=32, description='name of Media class (identifier)')
    desc: Optional[str] = Field(default='', max_length=64, description='description')
    codecs: List[CodecEnum] = Field(min_items=1, max_item=len(SWCODECS), description='sorted list of codec')
    codec_negotiation: NegotiationMode = Field(default='generous', description='codec negotiation mode, generous: refer remote, greedy: refer local,  scrooge: enforce local')
    media_mode: MediaModeEnum = Field(default='transcode', description='media processing mode')
    dtmf_mode: DtmfModeEnum = Field(default='rfc2833', description='Dual-tone multi-frequency mode')
    cng: bool = Field(default=False, description='comfort noise generate')
    vad: bool = Field(default=False, description='voice active detection, no transmit data when no party speaking')


@librerouter.post("/libreapi/class/media", status_code=200)
def create_media_class(reqbody: MediaModel, response: Response):
    result = None
    try:
        name = reqbody.name
        data = jsonable_encoder(reqbody)
        name_key = f'class:media:{name}'
        if rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent class name'}; return
        rdbconn.hmset(name_key, redishash(data))
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_media_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.put("/libreapi/class/media/{identifier}", status_code=200)
def update_media_class(reqbody: MediaModel, response: Response, identifier: str=Path(..., regex=_NAME_)):
    result = None
    try:
        pipe = rdbconn.pipeline()
        name = reqbody.name
        data = jsonable_encoder(reqbody)
        _name_key = f'class:media:{identifier}'
        name_key = f'class:media:{name}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent class identifier'}; return
        if name != identifier and rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent class name'}; return
        rdbconn.hmset(name_key, redishash(data))
        if name != identifier:
            _engaged_key = f'engagement:{_name_key}'
            engaged_key = f'engagement:{name_key}'
            engagements = rdbconn.smembers(_engaged_key)
            for engagement in engagements:
                pipe.hset(f'intcon:{engagement}', 'media_class', name)
            if rdbconn.exists(_engaged_key):
                pipe.rename(_engaged_key, engaged_key)
            pipe.delete(_name_key)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=update_media_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.delete("/libreapi/class/media/{identifier}", status_code=200)
def delete_media_class(response: Response, identifier: str=Path(..., regex=_NAME_)):
    result = None
    try:
        pipe = rdbconn.pipeline()
        _name_key = f'class:media:{identifier}'
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
        logify(f"module=liberator, space=libreapi, action=delete_media_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libreapi/class/media/{identifier}", status_code=200)
def detail_media_class(response: Response, identifier: str=Path(..., regex=_NAME_)):
    result = None
    try:
        _name_key = f'class:media:{identifier}'
        _engage_key = f'engagement:{_name_key}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent class identifier'}; return
        result = jsonhash(rdbconn.hgetall(_name_key))
        engagements = rdbconn.smembers(_engage_key)
        result.update({'engagements': engagements})
        response.status_code = 200
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=detail_media_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libreapi/class/media", status_code=200)
def list_media_class(response: Response):
    result = None
    try:
        pipe = rdbconn.pipeline()
        KEYPATTERN = f'class:media:*'
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
                data.append({'name': getaname(mainkey), 'desc': detail[0]})

        response.status_code, result = 200, data
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=list_media_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# CAPACITY
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
class CapacityModel(BaseModel):
    name: str = Field(regex=_NAME_, max_length=32, description='name of capacity class (identifier)')
    desc: Optional[str] = Field(default='', max_length=64, description='description')
    cps: int = Field(default=2, ge=-1, le=len(CLUSTERS.get('members'))*2000, description='call per second')
    concurentcalls: int = Field(default=10, ge=-1, le=len(CLUSTERS.get('members'))*25000, description='concurrent calls')
    # validator
    @root_validator()
    def capacity_agreement(cls, values):
        cps = values.get('cps')
        if cps > len(CLUSTERS.get('members'))*(CLUSTERS.get('max_calls_per_second'))//2:
            raise ValueError(f'the cps value is not valid for cluster capacity')
        concurentcalls = values.get('concurentcalls')
        if concurentcalls > len(CLUSTERS.get('members'))*(CLUSTERS.get('max_concurrent_calls'))//2:
            raise ValueError(f'the concurentcalls value is not valid for cluster capacity')
        return values


@librerouter.post("/libreapi/class/capacity", status_code=200)
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

@librerouter.put("/libreapi/class/capacity/{identifier}", status_code=200)
def update_capacity_class(reqbody: CapacityModel, response: Response, identifier: str=Path(..., regex=_NAME_)):
    result = None
    try:
        pipe = rdbconn.pipeline()
        name = reqbody.name
        data = jsonable_encoder(reqbody)
        _name_key = f'class:capacity:{identifier}'
        name_key = f'class:capacity:{name}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent class identifier'}; return
        if name != identifier and rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent class name'}; return
        rdbconn.hmset(name_key, redishash(data))
        if name != identifier:
            _engaged_key = f'engagement:{_name_key}'
            engaged_key = f'engagement:{name_key}'
            engagements = rdbconn.smembers(_engaged_key)
            for engagement in engagements:
                pipe.hset(f'intcon:{engagement}', 'capacity_class',  name)
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

@librerouter.delete("/libreapi/class/capacity/{identifier}", status_code=200)
def delete_capacity_class(response: Response, identifier: str=Path(..., regex=_NAME_)):
    result = None
    try:
        pipe = rdbconn.pipeline()
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

@librerouter.get("/libreapi/class/capacity/{identifier}", status_code=200)
def detail_capacity_class(response: Response, identifier: str=Path(..., regex=_NAME_)):
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

@librerouter.get("/libreapi/class/capacity", status_code=200)
def list_capacity_class(response: Response):
    result = None
    try:
        pipe = rdbconn.pipeline()
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
                data.append({'name': getaname(mainkey), 'desc': detail[0]})

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
    caller_number_pattern: str = Field(max_length=128, description='caller number pattern use pcre')
    destination_number_pattern: str = Field(max_length=128, description='destination number pattern use pcre')
    caller_number_replacement: str = Field(max_length=128, description='replacement that refer to caller number pattern use pcre')
    destination_number_replacement: str = Field(max_length=128, description='replacement that refer to destination number pattern use pcre')
    caller_name: Optional[str] = Field(default='_auto', max_length=128, description='set caller name, value can be any string or defined conventions: _auto, _caller_number(use caller id number as name)')

@librerouter.post("/libreapi/class/translation", status_code=200)
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

@librerouter.put("/libreapi/class/translation/{identifier}", status_code=200)
def update_translation_class(reqbody: TranslationModel, response: Response, identifier: str=Path(..., regex=_NAME_)):
    result = None
    try:
        pipe = rdbconn.pipeline()
        name = reqbody.name
        data = jsonable_encoder(reqbody)
        _name_key = f'class:translation:{identifier}'
        name_key = f'class:translation:{name}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent class identifier'}; return
        if name != identifier and rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent class name'}; return
        rdbconn.hmset(name_key, data)
        if name != identifier:
            _engaged_key = f'engagement:{_name_key}'
            engaged_key = f'engagement:{name_key}'
            engagements = rdbconn.smembers(_engaged_key)
            for engagement in engagements:
                _translation_rules = fieldjsonify(rdbconn.hget(f'intcon:{engagement}', 'translation_classes'))
                translation_rules = [name if rule == identifier else rule for rule in _translation_rules]
                pipe.hset(f'intcon:{engagement}', 'translation_classes', fieldredisify(translation_rules))
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

@librerouter.delete("/libreapi/class/translation/{identifier}", status_code=200)
def delete_translation_class(response: Response, identifier: str=Path(..., regex=_NAME_)):
    result = None
    try:
        pipe = rdbconn.pipeline()
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

@librerouter.get("/libreapi/class/translation/{identifier}", status_code=200)
def detail_translation_class(response: Response, identifier: str=Path(..., regex=_NAME_)):
    result = None
    try:
        _name_key = f'class:translation:{identifier}'
        _engaged_key = f'engagement:{_name_key}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent class identifier'}; return
        result = jsonhash(rdbconn.hgetall(_name_key))
        engagements = rdbconn.smembers(_engaged_key)
        result.update({'engagements': engagements})
        response.status_code = 200
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=detail_translation_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libreapi/class/translation", status_code=200)
def list_translation_class(response: Response):
    result = None
    try:
        pipe = rdbconn.pipeline()
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
                data.append({'name': getaname(mainkey), 'desc': detail[0]})
        response.status_code, result = 200, data
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=list_translation_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# MANIPULATION
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------

HANGUP_PATTERN = re.compile('^[A-Z][A-Z0-9_]+$')
NUMBER_PATTERN = re.compile('^[0-9]+$')

class ConditionLogic(str, Enum):
    AND = 'AND'
    OR = 'OR'

class ConditionRule(BaseModel):
    refervar: str = Field(min_length=2, max_length=128, description='variable name')
    pattern: Optional[str] = Field(min_length=2, max_length=128, description='variable pattern with regex')

class ManiCondition(BaseModel):
    logic: ConditionLogic = Field(default='AND', description='logic operation')
    rules: List[ConditionRule] = Field(min_items=1, max_items=8, description='list of condition expression')

class ActionEnum(str, Enum):
    set = 'set'
    log = 'log'
    hangup = 'hangup'
    sleep = 'sleep'

class ManiAction(BaseModel):
    action: ActionEnum = Field(description='action')
    refervar: Optional[str] = Field(min_length=2, max_length=128, description='name of reference variable')
    pattern: Optional[str] = Field(min_length=2, max_length=128, description='reference variable pattern with regex')
    targetvar: Optional[str] = Field(min_length=2, max_length=128, description='name of target variable')
    values: List[str] = Field(max_items=8, description='value of target variable')
    # validation
    @root_validator()
    def maniaction_agreement(cls, maniacts):
        _maniacts = jsonable_encoder(maniacts)
        action = _maniacts.get('action')
        values = _maniacts.get('values', [])
        if action == 'set':
            targetvar = _maniacts.get('targetvar')
            if not targetvar:
                raise ValueError(f'targetvar is require for {action} action')
            if not values:
                _maniacts.pop('refervar', None)
                _maniacts.pop('pattern', None)
        else: #{log,hangup,sleep}
            _maniacts.pop('targetvar', None)
            if not values:
                raise ValueError(f'values must contain at least 1 item for {action} action')
            else:
                if action == 'hangup':
                    if not HANGUP_PATTERN.match(values[0]):
                        raise ValueError(f'hangup action require define hangup cause string with upper charaters')
                    else:
                        _maniacts['values'] = values[:1]
                if action == 'sleep':
                    if not NUMBER_PATTERN.match(values[0]):
                        raise ValueError(f'sleep require value is a number')
                    else:
                        _maniacts['values'] = values[:1]

        return _maniacts

class ManipulationModel(BaseModel):
    name: str = Field(regex=_NAME_, max_length=32, description='name of manipulation class')
    desc: Optional[str] = Field(default='', max_length=64, description='description')
    conditions: Optional[ManiCondition] = Field(description='combine the logic and list of checking rules')
    actions: List[ManiAction] = Field(min_items=1, max_items=16, description='list of action when conditions is true')
    antiactions: Optional[List[ManiAction]] = Field(min_items=1, max_items=16, description='list of action when conditions is false')
    # validation
    @root_validator()
    def mani_agreement(cls, manis):
        _manis = jsonable_encoder(manis)
        if 'conditions' not in _manis:
            _manis.pop('antiactions', None)

        return _manis


@librerouter.post("/libreapi/class/manipulation", status_code=200)
def create_manipulation(reqbody: ManipulationModel, response: Response):
    requestid=get_request_uuid()
    result = None
    try:
        pipe = rdbconn.pipeline()
        name = reqbody.name
        data = jsonable_encoder(reqbody)
        name_key = f'class:manipulation:{name}'
        if rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent manipulation name'}; return
        rdbconn.hmset(name_key, redishash(data))
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_manipulation, requestid={requestid}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


@librerouter.put("/libreapi/class/manipulation/{identifier}", status_code=200)
def update_manipulation_class(reqbody: ManipulationModel, response: Response, identifier: str=Path(..., regex=_NAME_)):
    result = None
    try:
        pipe = rdbconn.pipeline()
        name = reqbody.name
        data = jsonable_encoder(reqbody)
        _name_key = f'class:manipulation:{identifier}'
        name_key = f'class:manipulation:{name}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent class identifier'}; return
        if name != identifier and rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent class name'}; return
        _data = jsonhash(rdbconn.hgetall(_name_key))
        rdbconn.hmset(name_key, redishash(data))
        # remove the unintended-field
        for _field in _data:
            if _field not in data:
                pipe.hdel(_name_key, _field)
        if name != identifier:
            _engaged_key = f'engagement:{_name_key}'
            engaged_key = f'engagement:{name_key}'
            engagements = rdbconn.smembers(_engaged_key)
            for engagement in engagements:
                _manipulation_rules = fieldjsonify(rdbconn.hget(f'intcon:{engagement}', 'manipulation_classes'))
                manipulation_rules = [name if rule == identifier else rule for rule in _manipulation_rules]
                pipe.hset(f'intcon:{engagement}', 'manipulation_classes', fieldredisify(manipulation_rules))
            if rdbconn.exists(_engaged_key):
                pipe.rename(_engaged_key, engaged_key)
            pipe.delete(_name_key)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=update_manipulation_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


@librerouter.delete("/libreapi/class/manipulation/{identifier}", status_code=200)
def delete_manipulation_class(response: Response, identifier: str=Path(..., regex=_NAME_)):
    result = None
    try:
        pipe = rdbconn.pipeline()
        _name_key = f'class:manipulation:{identifier}'
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
        logify(f"module=liberator, space=libreapi, action=delete_manipulation_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libreapi/class/manipulation/{identifier}", status_code=200)
def detail_manipulation_class(response: Response, identifier: str=Path(..., regex=_NAME_)):
    result = None
    try:
        _name_key = f'class:manipulation:{identifier}'
        _engaged_key = f'engagement:{_name_key}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent class identifier'}; return
        result = jsonhash(rdbconn.hgetall(_name_key))
        engagements = rdbconn.smembers(_engaged_key)
        result.update({'engagements': engagements})
        response.status_code = 200
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=detail_manipulation_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libreapi/class/manipulation", status_code=200)
def list_manipulation_class(response: Response):
    result = None
    try:
        pipe = rdbconn.pipeline()
        KEYPATTERN = f'class:manipulation:*'
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
                data.append({'name': getaname(mainkey), 'desc': detail[0]})
        response.status_code, result = 200, data
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=list_manipulation_class, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# GATEWAY
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
class TransportEnum(str, Enum):
    udp = "udp"
    tcp = "tcp"
    tls = "tls"

class CidTypeEnum(str, Enum):
    none = 'none'
    rpid = 'rpid'
    pid = 'pid'

class GatewayModel(BaseModel):
    name: str = Field(regex=_NAME_,min_length=2, max_length=32, description='name of translation class')
    desc: Optional[str] = Field(default='', max_length=64, description='description')
    username: str = Field(default='libre-user', min_length=1, max_length=128, description='username')
    auth_username: Optional[str] = Field(min_length=1, max_length=128, description='auth username', hidden_field=True)
    realm: Optional[str] = Field(min_length=1, max_length=256, description='auth realm, use gateway name as default')
    from_user: Optional[str] = Field(min_length=1, max_length=256, description='username in from header, use username as default')
    from_domain: Optional[str] = Field(min_length=1, max_length=256, description='domain in from header, use realm as default')
    password: str = Field(default='libre@secret', min_length=1, max_length=128, description='auth password')
    extension: Optional[str] = Field(max_length=256, description='extension for inbound calls, use username as default')
    proxy: str = Field(min_length=1, max_length=256, description='farend proxy ip address or domain, use realm as default')
    port: int = Field(default=5060, ge=0, le=65535, description='farend destination port')
    transport: TransportEnum = Field(default='udp', description='farend transport protocol')
    do_register: bool = Field(default=False, description='register to farend endpoint, false mean no register')
    register_proxy: Optional[str] = Field(min_length=1, max_length=256, description='proxy address to register, use proxy as default')
    register_transport: Optional[TransportEnum] = Field(description='transport to use for register')
    expire_seconds: Optional[int] = Field(ge=60, le=3600, description='register expire interval in second, use 600s as default')
    retry_seconds: Optional[int] = Field(ge=30, le=600, description='interval in second before a retry when a failure or timeout occurs')
    caller_id_in_from: bool = Field(default=True, description='use the callerid of an inbound call in the from field on outbound calls via this gateway')
    cid_type: Optional[CidTypeEnum] = Field(description='callerid header mechanism: rpid, pid, none')
    contact_params: Optional[str] = Field(min_length=1, max_length=256, description='extra sip params to send in the contact')
    contact_host: Optional[str] = Field(min_length=1, max_length=256, description='host part in contact header', hidden_field=True)
    extension_in_contact: Optional[bool] = Field(description='put the extension in the contact')
    ping: Optional[int] = Field(ge=5, le=3600, description='the period (second) to send SIP OPTION')
    ping_max: Optional[int] = Field(ge=1, le=31, description='number of success pings to declaring a gateway up')
    ping_min: Optional[int] = Field(ge=1, le=31,description='number of failure pings to declaring a gateway down')
    contact_in_ping: Optional[str] = Field(min_length=4, max_length=256, description='contact header of ping message', hidden_field=True)
    ping_user_agent: Optional[str] = Field(min_length=4, max_length=64, description='user agent of ping message', hidden_field=True)
    # validation
    @root_validator()
    def gateway_agreement(cls, values):
        _values = jsonable_encoder(values)
        for key, value in _values.items():
            if key == 'do_register' and not value:
                removekey(['register_proxy', 'register_transport', 'expire_seconds', 'retry_seconds'], values)

            if key == 'ping' and not value:
                removekey(['ping_max', 'ping_min', 'contact_in_ping', 'ping_user_agent'], values)

            if value is None:
                values.pop(key, None)

        for key, value in values.items():
            if key in ['realm', 'proxy', 'from_domain', 'register_proxy']:
                if not validators.ip_address.ipv4(value) and not validators.domain(value):
                    raise ValueError(f'{key} must be IPv4 address or Domain')
        return values

@librerouter.post("/libreapi/base/gateway", status_code=200)
def create_gateway(reqbody: GatewayModel, response: Response):
    requestid=get_request_uuid()
    result = None
    try:
        pipe = rdbconn.pipeline()
        name = reqbody.name
        data = jsonable_encoder(reqbody)
        name_key = f'base:gateway:{name}'
        if rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent gateway name'}; return
        rdbconn.hmset(name_key, redishash(data))
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_gateway, requestid={requestid}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.put("/libreapi/base/gateway/{identifier}", status_code=200)
def update_gateway(reqbody: GatewayModel, response: Response, identifier: str=Path(..., regex=_NAME_)):
    requestid=get_request_uuid()
    result = None
    try:
        pipe = rdbconn.pipeline()
        name = reqbody.name
        _name_key = f'base:gateway:{identifier}'
        name_key = f'base:gateway:{name}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent gateway identifier'}; return
        if name != identifier and rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent gateway name'}; return
        _data = jsonhash(rdbconn.hgetall(_name_key))
        data = jsonable_encoder(reqbody)
        rdbconn.hmset(name_key, redishash(data))
        # remove the unintended-field
        for _field in _data:
            if _field not in data:
                pipe.hdel(_name_key, _field)
        # if change name
        _engaged_key = f'engagement:{_name_key}'
        engaged_key = f'engagement:{name_key}'
        if name != identifier:
            engagements = rdbconn.smembers(_engaged_key)
            for engagement in engagements:
                weight = rdbconn.hget(f'intcon:out:{engagement}:_gateways', identifier)
                pipe.hdel(f'intcon:out:{engagement}:_gateways', identifier)
                pipe.hset(f'intcon:out:{engagement}:_gateways', name, weight)
            if rdbconn.exists(_engaged_key):
                pipe.rename(_engaged_key, engaged_key)
            pipe.delete(_name_key)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
        # fire event for update gateway only if gatetway in used
        intconname = rdbconn.srandmember(engaged_key); sipprofile = None
        if intconname:
            sipprofile = rdbconn.hget(f'intcon:out:{intconname}', 'sipprofile')
        if sipprofile:
            rdbconn.publish(CHANGE_CFG_CHANNEL, json.dumps({'portion': 'sofiagw', 'action': 'update', 'gateway': name, '_gateway': identifier, 'sipprofile': sipprofile, 'requestid': requestid}))
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=update_gateway, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.delete("/libreapi/base/gateway/{identifier}", status_code=200)
def delete_gateway(response: Response, identifier: str=Path(..., regex=_NAME_)):
    requestid=get_request_uuid()
    result = None
    try:
        pipe = rdbconn.pipeline()
        _name_key = f'base:gateway:{identifier}'
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
        logify(f"module=liberator, space=libreapi, action=delete_gateway, requestid={requestid}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libreapi/base/gateway/{identifier}", status_code=200)
def detail_gateway(response: Response, identifier: str=Path(..., regex=_NAME_)):
    result = None
    try:
        _name_key = f'base:gateway:{identifier}'
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

@librerouter.get("/libreapi/base/gateway", status_code=200)
def list_gateway(response: Response):
    result = None
    try:
        pipe = rdbconn.pipeline()
        KEYPATTERN = f'base:gateway:*'
        next, mainkeys = rdbconn.scan(0, KEYPATTERN, SCAN_COUNT)
        while next:
            next, tmpkeys = rdbconn.scan(next, KEYPATTERN, SCAN_COUNT)
            mainkeys += tmpkeys

        for mainkey in mainkeys:
            pipe.hmget(mainkey, 'desc', 'proxy', 'port', 'transport')
        details = pipe.execute()

        data = list()
        for mainkey, detail in zip(mainkeys, details):
            if detail:
                data.append(jsonhash({'name': getaname(mainkey), 'desc': detail[0], 'ip': detail[1], 'port': detail[2], 'transport': detail[3]}))

        response.status_code, result = 200, data
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=list_gateway, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------

def check_existent_media(name):
    if not rdbconn.exists(f'class:media:{name}'):
        raise ValueError('nonexistent class')
    return name

def check_existent_capacity(capacity):
    if not rdbconn.exists(f'class:capacity:{capacity}'):
        raise ValueError('nonexistent class')
    return capacity

def check_existent_manipulation(manipulations):
    for manipulation in manipulations:
        if not rdbconn.exists(f'class:manipulation:{manipulation}'):
            raise ValueError('nonexistent class')
    return manipulations

def check_existent_translation(translations):
    for translation in translations:
        if not rdbconn.exists(f'class:translation:{translation}'):
            raise ValueError('nonexistent class')
    return translations

def check_existent_sipprofile(sipprofile):
    if not rdbconn.exists(f'sipprofile:{sipprofile}'):
        raise ValueError('nonexistent sipprofile')
    return sipprofile

def check_cluster_node(nodes):
    for node in nodes:
        if node != '_ALL_' and node not in CLUSTERS.get('members'):
            raise ValueError('nonexistent node')
    return nodes


#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# OUTBOUND INTERCONECTION
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------

WEIGHTBASE = 'weight_based'
ROUNDROBIN = 'round_robin'
HASHCALLID = 'hash_callid'
HASHIPADDR = 'hash_src_ip'
HASHDESTNO = 'hash_destination_number'

class Distribution(str, Enum):
    weight_based = WEIGHTBASE
    round_robin = ROUNDROBIN
    hash_callid = HASHCALLID
    hash_src_ip = HASHIPADDR
    hash_destination_number = HASHDESTNO

class PrivacyEnum(str, Enum):
    auto = 'auto'
    none = 'none'
    screen = 'screen'
    name = 'name'
    number = 'number'

class CallerIDType(str, Enum):
    auto = 'auto'
    none = 'none'
    rpid = 'rpid'
    pid = 'pid'

class DistributedGatewayModel(BaseModel):
    name: str = Field(regex=_NAME_, max_length=32, description='gateway name')
    weight: int = Field(default=1, ge=0, le=127, description='weight value use for distribution')

class OutboundInterconnection(BaseModel):
    name: str = Field(regex=_NAME_, max_length=32, description='name of outbound interconnection')
    desc: Optional[str] = Field(default='', max_length=64, description='description')
    sipprofile: str = Field(description='a sip profile nameid that interconnection engage to')
    distribution: Distribution = Field(default='round_robin', description='The dispatcher algorithm to selects a destination from addresses set')
    gateways: List[DistributedGatewayModel] = Field(min_items=1, max_item=10, description='gateways list used for this interconnection')
    rtpaddrs: List[IPv4Network] = Field(min_items=0, max_item=20, description='a set of IPv4 Network that use for RTP')
    media_class: str = Field(description='nameid of media class')
    capacity_class: str = Field(description='nameid of capacity class')
    translation_classes: List[str] = Field(default=[], min_items=0, max_item=5, description='a set of translation class')
    manipulation_classes: List[str] = Field(default=[], min_items=0, max_item=5, description='a set of manipulations class')
    privacy: List[PrivacyEnum] = Field(default=['auto'], min_items=1, max_item=3, description='privacy header')
    cid_type: Optional[CallerIDType] = Field(default='auto', description='callerid header mechanism: rpid, pid, none')
    nodes: List[str] = Field(default=['_ALL_'], min_items=1, max_item=len(CLUSTERS.get('members')), description='a set of node member that interconnection engage to')
    enable: bool = Field(default=True, description='enable/disable this interconnection')
    # validation
    _existentmedia = validator('media_class', allow_reuse=True)(check_existent_media)
    _existentcapacity = validator('capacity_class', allow_reuse=True)(check_existent_capacity)
    _existenttranslation = validator('translation_classes', allow_reuse=True)(check_existent_translation)
    _existentmanipulation = validator('manipulation_classes', allow_reuse=True)(check_existent_manipulation)
    _existentsipprofile = validator('sipprofile', allow_reuse=True)(check_existent_sipprofile)
    _clusternode = validator('nodes', allow_reuse=True)(check_cluster_node)

    @root_validator()
    def out_intcon_agreement(cls, values):
        values = jsonable_encoder(values)
        sipprofile = values.get('sipprofile')
        distribution = values.get('distribution')
        gateways = values.get('gateways')
        for gateway in gateways:
            gwname = gateway.get('name')
            # check if gateways is existing
            if not rdbconn.exists(f'base:gateway:{gwname}'):
                raise ValueError('nonexistent gateway')

            # gateway agreement with inteconnection and sipprofile
            _intcon = rdbconn.srandmember(f'engagement:base:gateway:{gateway}')
            if _intcon:
                _scard = rdbconn.scard(f'engagement:base:gateway:{gateway}')
                _sipprofile = rdbconn.hget(f'intcon:{_intcon}', 'sipprofile')
                if sipprofile != _sipprofile and _scard > 1:
                    raise ValueError('gateway can be assigned to multiple intconnection only if they use the same sip profile')

            if distribution != WEIGHTBASE:
                gateway['weight'] = 1

        privacy = values.get('privacy')
        privacilen = len(privacy)
        if 'none' in privacy and privacilen > 1: raise ValueError('none can not configured with others')
        elif 'auto' in privacy:
            if privacilen > 1 and ('number' in privacy or 'name' in privacy):
                raise ValueError('auto can not configured with others except screen')
        else: pass

        return values


@librerouter.post("/libreapi/interconnection/outbound", status_code=200)
def create_outbound_interconnection(reqbody: OutboundInterconnection, response: Response):
    requestid = get_request_uuid()
    result = None
    try:
        pipe = rdbconn.pipeline()
        name = reqbody.name
        data = jsonable_encoder(reqbody)
        sipprofile = data.get('sipprofile')
        gateways = {gw.get('name'):gw.get('weight') for gw in data.get('gateways')}
        rtpaddrs = set(data.get('rtpaddrs'))
        media_class = data.get('media_class')
        capacity_class = data.get('capacity_class')
        translation_classes = data.get('translation_classes')
        manipulation_classes = data.get('manipulation_classes')
        nodes = set(data.get('nodes'))
        # verification
        nameid = f'out:{name}'; name_key = f'intcon:{nameid}'
        if rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent outbound interconnection'}; return
        # processing
        data.pop('gateways'); data.update({'rtpaddrs': rtpaddrs, 'nodes': nodes })
        pipe.hmset(name_key, redishash(data))
        pipe.sadd(f'engagement:sipprofile:{sipprofile}', nameid)
        for node in nodes: pipe.sadd(f'engagement:node:{node}', nameid)
        pipe.sadd(f'engagement:class:media:{media_class}', nameid)
        pipe.sadd(f'engagement:class:capacity:{capacity_class}', nameid)
        for translation in translation_classes: pipe.sadd(f'engagement:class:translation:{translation}', nameid)
        for manipulation in manipulation_classes: pipe.sadd(f'engagement:class:manipulation:{manipulation}', nameid)
        pipe.hmset(f'intcon:{nameid}:_gateways', redishash(gateways))
        for gateway in gateways: pipe.sadd(f'engagement:base:gateway:{gateway}', name)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
        # fire-event outbound interconnect create
        rdbconn.publish(CHANGE_CFG_CHANNEL, json.dumps({'portion': 'outbound:intcon', 'action': 'create', 'intcon': name, 'sipprofile': sipprofile, 'requestid': requestid}))
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_outbound_interconnection, requestid={requestid}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.put("/libreapi/interconnection/outbound/{identifier}", status_code=200)
def update_outbound_interconnection(reqbody: OutboundInterconnection, response: Response, identifier: str=Path(..., regex=_NAME_)):
    requestid = get_request_uuid()
    result = None
    try:
        pipe = rdbconn.pipeline()
        name = reqbody.name
        data = jsonable_encoder(reqbody)
        sipprofile = data.get('sipprofile')
        gateways = {gw.get('name'):gw.get('weight') for gw in data.get('gateways')}
        rtpaddrs = set(data.get('rtpaddrs'))
        media_class = data.get('media_class')
        capacity_class = data.get('capacity_class')
        translation_classes = data.get('translation_classes')
        manipulation_classes = data.get('manipulation_classes')
        nodes = set(data.get('nodes'))
        # verification
        nameid = f'out:{name}'; name_key = f'intcon:{nameid}'
        _nameid = f'out:{identifier}'; _name_key = f'intcon:{_nameid}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent outbound interconnection identifier'}; return
        if name != identifier and rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent outbound interconnection name'}; return
        # get current data
        _data = jsonhash(rdbconn.hgetall(_name_key))
        _sipprofile = _data.get('sipprofile')
        _nodes = _data.get('nodes')
        _media_class = _data.get('media_class')
        _capacity_class = _data.get('capacity_class')
        _translation_classes = _data.get('translation_classes')
        _manipulation_classes = _data.get('manipulation_classes')
        _sipaddrs = _data.get('sipaddrs')
        _gateways = jsonhash(rdbconn.hgetall(f'{_name_key}:_gateways'))
        # transaction block
        pipe.multi()
        # processing: removing old-one
        pipe.srem(f'engagement:sipprofile:{_sipprofile}', _nameid)
        for node in _nodes: pipe.srem(f'engagement:node:{node}', _nameid)
        pipe.srem(f'engagement:class:media:{_media_class}', _nameid)
        pipe.srem(f'engagement:class:capacity:{_capacity_class}', _nameid)
        for translation in _translation_classes: pipe.srem(f'engagement:class:translation:{translation}', _nameid)
        for manipulation in _manipulation_classes: pipe.srem(f'engagement:class:manipulation:{manipulation}', _nameid)
        # remove intcon out of the  gateways engagement list, and built the map of gateway and number of intcon use this gateway
        _gws =  dict()
        for gateway in _gateways:
            gw_engaged_key = f'engagement:base:gateway:{gateway}'
            _gws[gateway] = rdbconn.scard(gw_engaged_key)
            pipe.srem(gw_engaged_key, identifier)

        pipe.delete(f'{_name_key}:_gateways')
        # processing: adding new-one
        data.pop('gateways'); data.update({'rtpaddrs': rtpaddrs, 'nodes': nodes })
        pipe.hmset(name_key, redishash(data))
        pipe.sadd(f'engagement:sipprofile:{sipprofile}', nameid)
        for node in nodes: pipe.sadd(f'engagement:node:{node}', nameid)
        pipe.sadd(f'engagement:class:media:{media_class}', nameid)
        pipe.sadd(f'engagement:class:capacity:{capacity_class}', nameid)
        for translation in translation_classes: pipe.sadd(f'engagement:class:translation:{translation}', nameid)
        for manipulation in manipulation_classes: pipe.sadd(f'engagement:class:manipulation:{manipulation}', nameid)
        pipe.hmset(f'{name_key}:_gateways', redishash(gateways))
        for gateway in gateways: pipe.sadd(f'engagement:base:gateway:{gateway}', name)
        # remove the unintended-field
        for _field in _data:
            if _field not in data:
                pipe.hdel(_name_key, _field)
        # change identifier
        if name != identifier:
            _engaged_key = f'engagement:{_name_key}'
            engaged_key = f'engagement:{name_key}'
            engagements = rdbconn.smembers(_engaged_key)
            for engagement in engagements:
                if engagement.startswith('table'):
                    _endpoints = fieldjsonify(rdbconn.hget(f'routing:{engagement}', 'endpoints'))
                    if _endpoints:
                        endpoints = [name if endpoint == identifier else endpoint for endpoint in _endpoints]
                        pipe.hset(f'routing:{engagement}', 'endpoints', fieldredisify(endpoints))
                if engagement.startswith('record'):
                    _endpoints = fieldjsonify(rdbconn.hget(f'routing:{engagement}', 'endpoints'))
                    _action = rdbconn.hget(f'routing:{engagement}', 'action')
                    if _endpoints and _action==_ROUTE:
                        endpoints = [name if endpoint == identifier else endpoint for endpoint in _endpoints]
                        pipe.hset(f'routing:{engagement}', 'endpoints', fieldredisify(endpoints))
            if rdbconn.exists(_engaged_key):
                pipe.rename(_engaged_key, engaged_key)
            pipe.delete(_name_key)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
        # fire-event outbound interconnect update only if gateway or sipprofile change
        if sipprofile != _sipprofile or set(gateways.keys()) == set(_gateways.keys()):
            rdbconn.publish(CHANGE_CFG_CHANNEL, json.dumps({'portion': 'outbound:intcon', 'action': 'update', 'intcon': name, '_intcon': identifier, 'sipprofile': sipprofile, '_sipprofile': _sipprofile, 'gateways': list(gateways.keys()), '_gateways': _gws, 'requestid': requestid}))
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=update_outbound_interconnection, requestid={requestid}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.delete("/libreapi/interconnection/outbound/{identifier}", status_code=200)
def delete_outbound_interconnection(response: Response, identifier: str=Path(..., regex=_NAME_)):
    requestid = get_request_uuid()
    result = None
    try:
        pipe = rdbconn.pipeline()
        _nameid = f'out:{identifier}'; _name_key = f'intcon:{_nameid}'
        _engaged_key = f'engagement:{_name_key}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent outbound interconnection identifier'}; return
        if rdbconn.scard(_engaged_key):
            response.status_code, result = 403, {'error': 'engaged outbound interconnection'}; return
        # get current data
        _data = jsonhash(rdbconn.hgetall(_name_key))
        _sipprofile = _data.get('sipprofile')
        _nodes = _data.get('nodes')
        _media_class = _data.get('media_class')
        _capacity_class = _data.get('capacity_class')
        _translation_classes = _data.get('translation_classes')
        _manipulation_classes = _data.get('manipulation_classes')
        _sipaddrs = _data.get('sipaddrs')
        _gateways = jsonhash(rdbconn.hgetall(f'{_name_key}:_gateways'))
        # processing: removing old-one
        pipe.srem(f'engagement:sipprofile:{_sipprofile}', _nameid)
        for node in _nodes: pipe.srem(f'engagement:node:{node}', _nameid)
        pipe.srem(f'engagement:class:media:{_media_class}', _nameid)
        pipe.srem(f'engagement:class:capacity:{_capacity_class}', _nameid)
        for translation in _translation_classes: pipe.srem(f'engagement:class:translation:{translation}', _nameid)
        for manipulation in _manipulation_classes: pipe.srem(f'engagement:class:manipulation:{manipulation}', _nameid)
        # remove intcon out of the  gateways engagement list, and built the map of gateway and number of intcon use this gateway
        _gws =  dict()
        for gateway in _gateways:
            gw_engaged_key = f'engagement:base:gateway:{gateway}'
            _gws[gateway] = rdbconn.scard(gw_engaged_key)
            pipe.srem(gw_engaged_key, identifier)

        pipe.delete(f'{_name_key}:_gateways')
        pipe.delete(_name_key)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
        # fire-event outbound interconnect update
        if _gws:
            rdbconn.publish(CHANGE_CFG_CHANNEL, json.dumps({'portion': 'outbound:intcon', 'action': 'delete', '_intcon': identifier, '_sipprofile': _sipprofile, '_gateways': _gws, 'requestid': requestid}))
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=delete_outbound_interconnection, requestid={requestid}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libreapi/interconnection/outbound/{identifier}", status_code=200)
def detail_outbound_interconnection(response: Response, identifier: str=Path(..., regex=_NAME_)):
    result = None
    try:
        _nameid = f'out:{identifier}'
        _name_key = f'intcon:{_nameid}'
        _engaged_key = f'engagement:{_name_key}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent outbound interconnection identifier'}; return
        result = jsonhash(rdbconn.hgetall(_name_key))
        gateways = [{'name': k, 'weight': v} for k,v in jsonhash(rdbconn.hgetall(f'intcon:{_nameid}:_gateways')).items()]
        engagements = rdbconn.smembers(_engaged_key)
        result.update({'gateways': gateways, 'engagements': engagements})
        response.status_code = 200
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=detail_outbound_interconnection, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
@librerouter.get("/libreapi/interconnection/outbound", status_code=200)
def list_outbound_interconnect(response: Response):
    result = None
    try:
        pipe = rdbconn.pipeline()
        KEYPATTERN = 'intcon:out:*'
        next, mainkeys = rdbconn.scan(0, KEYPATTERN, SCAN_COUNT)
        while next:
            next, tmpkeys = rdbconn.scan(next, KEYPATTERN, SCAN_COUNT)
            mainkeys += tmpkeys

        for mainkey in mainkeys:
            pipe.hmget(mainkey, 'name', 'desc', 'sipprofile')
        details = pipe.execute()

        data = list(); PYPATTERN = re.compile('^intcon:out:[^:]+$')
        for mainkey, detail in zip(mainkeys, details):
            if PYPATTERN.match(mainkey):
                data.append({'name': detail[0], 'desc': detail[1], 'sipprofile': detail[2]})

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
    if not rdbconn.exists(f'routing:table:{table}'):
        raise ValueError('nonexistent routing')
    return table

def check_existent_preanswer(preanswer):
    if preanswer:
        if not rdbconn.exists(f'class:preanswer:{preanswer}'):
            raise ValueError('nonexistent class')
    return preanswer

class AuthSchemeEnum(str, Enum):
    IP = 'IP'
    DIGEST = 'DIGEST'
    BOTH = 'BOTH'

class InboundInterconnection(BaseModel):
    name: str = Field(regex=_NAME_, max_length=32, description='name of inbound interconnection')
    desc: Optional[str] = Field(default='', max_length=64, description='description')
    sipprofile: str = Field(description='a sip profile nameid that interconnection engage to')
    routing: str = Field(description='routing table that will be used by this inbound interconnection')
    sipaddrs: List[IPv4Network] = Field(min_items=1, max_item=16, description='set of sip signalling addresses that use for SIP')
    rtpaddrs: List[IPv4Network] = Field(min_items=0, max_item=20, description='a set of IPv4 Network that use for RTP')
    ringready: bool = Field(default=False, description='response 180 ring indication')
    media_class: str = Field(description='nameid of media class')
    capacity_class: str = Field(description='nameid of capacity class')
    translation_classes: List[str] = Field(default=[], min_items=0, max_item=5, description='a set of translation class')
    manipulation_classes: List[str] = Field(default=[], min_items=0, max_item=5, description='a set of manipulations class')
    preanswer_class: str = Field(default=None, description='nameid of preanswer class')
    authscheme: AuthSchemeEnum = Field(default='IP', description='auth scheme for inbound, include: ip, digest, both')
    secret: Optional[str] = Field(min_length=8, max_length=64, description='password of digest auth for inbound', hidden_field=True)
    nodes: List[str] = Field(default=['_ALL_'], min_items=1, max_item=len(CLUSTERS.get('members')), description='a set of node member that interconnection engage to')
    enable: bool = Field(default=True, description='enable/disable this interconnection')
    # validation
    _existenpreanswer = validator('preanswer_class', allow_reuse=True)(check_existent_preanswer)
    _existentmedia = validator('media_class', allow_reuse=True)(check_existent_media)
    _existentcapacity = validator('capacity_class', allow_reuse=True)(check_existent_capacity)
    _existenttranslation = validator('translation_classes', allow_reuse=True)(check_existent_translation)
    _existentmanipulation = validator('manipulation_classes', allow_reuse=True)(check_existent_translation)
    _existentsipprofile = validator('sipprofile', allow_reuse=True)(check_existent_sipprofile)
    _existentrouting = validator('routing')(check_existent_routing)
    _clusternode = validator('nodes', allow_reuse=True)(check_cluster_node)

    @root_validator()
    def in_intcon_agreement(cls, values):
        _values = jsonable_encoder(values)
        authscheme = _values.get('authscheme')
        secret = _values.get('secret')
        if authscheme != 'IP' and not secret:
            raise ValueError(f'auth scheme {authscheme} require define secret')
        for key, value in values.items():
            if value is None:
                _values.pop(key, None)
        return _values


@librerouter.post("/libreapi/interconnection/inbound", status_code=200)
def create_inbound_interconnection(reqbody: InboundInterconnection, response: Response):
    requestid=get_request_uuid()
    result = None
    try:
        pipe = rdbconn.pipeline()
        name = reqbody.name
        data = jsonable_encoder(reqbody)
        sipprofile = data.get('sipprofile')
        routing = data.get('routing')
        sipaddrs = set(data.get('sipaddrs'))
        rtpaddrs = set(data.get('rtpaddrs'))
        media_class = data.get('media_class')
        preanswer_class = data.get('preanswer_class')
        capacity_class = data.get('capacity_class')
        translation_classes = data.get('translation_classes')
        manipulation_classes = data.get('manipulation_classes')
        nodes = set(data.get('nodes'))
        # verification
        nameid = f'in:{name}'; name_key = f'intcon:{nameid}'
        if rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent inbound interconnection'}; return
        # guaranted that the address not overlap eachother
        _farendsipaddrs = rdbconn.smembers(f'farendsipaddrs:in:{sipprofile}')
        for sipaddr in sipaddrs:
            cidr = IPv4Network(sipaddr)
            for _farendsipaddr in _farendsipaddrs:
                _cidr = IPv4Network(_farendsipaddr)
                if _cidr.overlaps(cidr):
                        response.status_code, result = 403, {'error': f'These addresses {sipaddr} & {_farendsipaddr} are overlaped'}; return
        # processing
        data.update({'sipaddrs': sipaddrs, 'rtpaddrs': rtpaddrs, 'nodes': nodes })
        pipe.hmset(name_key, redishash(data))
        pipe.sadd(f'engagement:sipprofile:{sipprofile}', nameid)
        pipe.sadd(f'engagement:routing:table:{routing}', nameid)
        for node in nodes: pipe.sadd(f'engagement:node:{node}', nameid)
        pipe.sadd(f'engagement:class:media:{media_class}', nameid)
        if preanswer_class:
            pipe.sadd(f'engagement:class:preanswer:{preanswer_class}', nameid)
        pipe.sadd(f'engagement:class:capacity:{capacity_class}', nameid)
        for translation in translation_classes: pipe.sadd(f'engagement:class:translation:{translation}', nameid)
        for manipulation in manipulation_classes: pipe.sadd(f'engagement:class:manipulation:{manipulation}', nameid)
        for sipaddr in sipaddrs: pipe.sadd(f'farendsipaddrs:in:{sipprofile}', sipaddr)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
        # fire-event inbound interconnect create
        rdbconn.publish(CHANGE_CFG_CHANNEL, json.dumps({'portion': 'inbound:intcon', 'action': 'create', 'intcon': name, 'requestid': requestid}))
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_inbound_interconnection, requestid={requestid}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


@librerouter.put("/libreapi/interconnection/inbound/{identifier}", status_code=200)
def update_inbound_interconnection(reqbody: InboundInterconnection, response: Response, identifier: str=Path(..., regex=_NAME_)):
    requestid=get_request_uuid()
    result = None
    try:
        pipe = rdbconn.pipeline()
        name = reqbody.name
        data = jsonable_encoder(reqbody)
        sipprofile = data.get('sipprofile')
        sipaddrs = set(data.get('sipaddrs'))
        rtpaddrs = set(data.get('rtpaddrs'))
        routing = data.get('routing')
        media_class = data.get('media_class')
        preanswer_class = data.get('preanswer_class')
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
        # get current data
        _data = jsonhash(rdbconn.hgetall(_name_key))
        _sipprofile = _data.get('sipprofile')
        _routing = _data.get('routing')
        _nodes = set(_data.get('nodes'))
        _media_class = _data.get('media_class')
        _preanswer_class = _data.get('preanswer_class')
        _capacity_class = _data.get('capacity_class')
        _translation_classes = _data.get('translation_classes')
        _manipulation_classes = _data.get('manipulation_classes')
        _sipaddrs = set(_data.get('sipaddrs'))
        # verification
        if sipprofile == _sipprofile: newaddrs = sipaddrs - _sipaddrs
        else: newaddrs = sipaddrs
        if newaddrs:
            _farendsipaddrs = rdbconn.smembers(f'farendsipaddrs:in:{_sipprofile}')
            for newaddr in newaddrs:
                cidr = IPv4Network(newaddr)
                for _farendsipaddr in _farendsipaddrs:
                    _cidr = IPv4Network(_farendsipaddr)
                    if _cidr.overlaps(cidr):
                            response.status_code, result = 403, {'error': f'These addresses {newaddr} & {_farendsipaddr} are overlaped'}; return
        # transaction block
        pipe.multi()
        # processing: removing old-one
        pipe.srem(f'engagement:sipprofile:{_sipprofile}', _nameid)
        pipe.srem(f'engagement:routing:table:{_routing}', _nameid)
        for node in _nodes: pipe.srem(f'engagement:node:{node}', _nameid)
        pipe.srem(f'engagement:class:media:{_media_class}', _nameid)
        if _preanswer_class:
            pipe.srem(f'engagement:class:preanswer:{_preanswer_class}', _nameid)
        pipe.srem(f'engagement:class:capacity:{_capacity_class}', _nameid)
        for translation in _translation_classes: pipe.srem(f'engagement:class:translation:{translation}', _nameid)
        for manipulation in _manipulation_classes: pipe.srem(f'engagement:class:manipulation:{manipulation}', _nameid)
        if sipprofile == _sipprofile:
            oldaddrs = _sipaddrs - sipaddrs
            for oldaddr in oldaddrs: pipe.srem(f'farendsipaddrs:in:{_sipprofile}', oldaddr)
        # processing: adding new-one
        data.update({'sipaddrs': sipaddrs, 'rtpaddrs': rtpaddrs, 'nodes': nodes })
        pipe.hmset(name_key, redishash(data))
        pipe.sadd(f'engagement:sipprofile:{sipprofile}', nameid)
        pipe.sadd(f'engagement:routing:table:{routing}', nameid)
        for node in nodes: pipe.sadd(f'engagement:node:{node}', nameid)
        pipe.sadd(f'engagement:class:media:{media_class}', nameid)
        if preanswer_class:
            pipe.sadd(f'engagement:class:preanswer:{preanswer_class}', nameid)
        pipe.sadd(f'engagement:class:capacity:{capacity_class}', nameid)
        for translation in translation_classes: pipe.sadd(f'engagement:class:translation:{translation}', nameid)
        for manipulation in manipulation_classes: pipe.sadd(f'engagement:class:manipulation:{manipulation}', nameid)
        for newaddr in newaddrs: pipe.sadd(f'farendsipaddrs:in:{sipprofile}', newaddr)
        # remove the unintended-field
        for _field in _data:
            if _field not in data:
                pipe.hdel(_name_key, _field)
        # change identifier
        if name != identifier:
            pipe.delete(_name_key)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
        # fire-event inbound interconnect update
        rdbconn.publish(CHANGE_CFG_CHANNEL, json.dumps({'portion': 'inbound:intcon', 'action': 'update', 'intcon': name, '_intcon': identifier, 'requestid': requestid}))
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=update_inbound_interconnection, requestid={requestid}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


@librerouter.delete("/libreapi/interconnection/inbound/{identifier}", status_code=200)
def delete_inbound_interconnection(response: Response, identifier: str=Path(..., regex=_NAME_)):
    requestid=get_request_uuid()
    result = None
    try:
        pipe = rdbconn.pipeline()
        _nameid = f'in:{identifier}'; _name_key = f'intcon:{_nameid}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent inbound interconnection'}; return

        _data = jsonhash(rdbconn.hgetall(_name_key))
        _sipprofile = _data.get('sipprofile')
        _nodes = _data.get('nodes')
        _media_class = _data.get('media_class')
        _preanswer_class = _data.get('preanswer_class')
        _capacity_class = _data.get('capacity_class')
        _translation_classes = _data.get('translation_classes')
        _manipulation_classes = _data.get('manipulation_classes')
        _sipaddrs = _data.get('sipaddrs')

        pipe.srem(f'engagement:sipprofile:{_sipprofile}', _nameid)
        for node in _nodes: pipe.srem(f'engagement:node:{node}', _nameid)
        pipe.srem(f'engagement:class:media:{_media_class}', _nameid)
        if _preanswer_class:
            pipe.srem(f'engagement:class:preanswer:{_preanswer_class}', _nameid)
        pipe.srem(f'engagement:class:capacity:{_capacity_class}', _nameid)
        for translation in _translation_classes: pipe.srem(f'engagement:class:translation:{translation}', _nameid)
        for manipulation in _manipulation_classes: pipe.srem(f'engagement:class:manipulation:{manipulation}', _nameid)
        for _sipaddr in _sipaddrs: pipe.srem(f'farendsipaddrs:in:{_sipprofile}', _sipaddr)
        pipe.delete(_name_key)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
        # fire-event inbound interconnect delete
        rdbconn.publish(CHANGE_CFG_CHANNEL, json.dumps({'portion': 'inbound:intcon', 'action': 'delete', '_intcon': identifier, 'requestid': requestid}))
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=delete_inbound_interconnection, requestid={requestid}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


@librerouter.get("/libreapi/interconnection/inbound/{identifier}", status_code=200)
def detail_inbound_interconnection(response: Response, identifier: str=Path(..., regex=_NAME_)):
    result = None
    try:
        _name_key = f'intcon:in:{identifier}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent inbound interconnection identifier'}; return
        result = jsonhash(rdbconn.hgetall(_name_key))
        response.status_code = 200
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=detail_inbound_interconnection, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


@librerouter.get("/libreapi/interconnection/inbound", status_code=200)
def list_inbound_interconnect(response: Response):
    result = None
    try:
        pipe = rdbconn.pipeline()
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
            data.append({'name': getaname(mainkey), 'desc': detail[0], 'sipprofile': detail[1], 'routing': detail[2]})

        response.status_code, result = 200, data
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=list_inbound_interconnect, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ROUTING TABLE
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
class RouteModel(BaseModel):
    primary: str = Field(description='primary entity of route')
    secondary: str = Field(description='secondary entity of route')
    load: int = Field(ge=0, le=100, description='load sharing value for between 2 routes')

class RoutingTableActionEnum(str, Enum):
    query = _QUERY
    route = _ROUTE
    block = _BLOCK
    # request: reseved routing with http api
class RoutingVariableEnum(str, Enum):
    cidnumber = 'cidnumber'
    cidname = 'cidname'
    dstnumber = 'dstnumber'
    intconname = 'intconname'
    realm = 'realm'

class RoutingTableModel(BaseModel):
    name: str = Field(regex=_NAME_, max_length=32, description='name of routing table')
    desc: Optional[str] = Field(default='', max_length=64, description='description')
    variables: Optional[List[str]] = Field(min_items=1, max_items=5, description='sip variable for routing base, eg: cidnumber, cidname, dstnumber, intconname, realm')
    action: RoutingTableActionEnum = Field(default='query', description=f'routing action: {_QUERY} - find nexthop by query routing record; {_BLOCK} - block the call; {_ROUTE} - route call to outbound interconnection')
    routes: Optional[RouteModel] = Field(description='route model data')
    # validation
    @root_validator()
    def routing_table_agreement(cls, values):
        values = jsonable_encoder(values)
        action = values.get('action')
        if action==_ROUTE:
            values.pop('variables', None)
            routes = values.get('routes', None)
            if not routes:
                raise ValueError(f'{_ROUTE} action require at routes param')
            else:
                primary = routes.get('primary')
                secondary = routes.get('secondary')
                load = routes.get('load')
                for intconname in [primary, secondary]:
                    if not rdbconn.exists(f'intcon:out:{intconname}'):
                        raise ValueError('nonexistent outbound interconnect')
                values['routes'] = [primary, secondary, load]
        elif action==_QUERY:
            values.pop('routes', None)
            variables = values.get('variables')
            if not variables:
                raise ValueError(f'{_QUERY} action require at variables param')
            else:
                values['variables'] = variables[:1]
        else:
            values.pop('routes', None)
            values.pop('variables', None)

        return values


@librerouter.post("/libreapi/routing/table", status_code=200)
def create_routing_table(reqbody: RoutingTableModel, response: Response):
    result = None
    try:
        pipe = rdbconn.pipeline()
        name = reqbody.name
        nameid = f'table:{name}'; name_key = f'routing:{nameid}'
        if rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent routing table'}; return

        data = jsonable_encoder(reqbody)
        pipe.hmset(name_key, redishash(data))
        routes = data.get('routes')
        if routes:
            for route in routes[:2]:
                pipe.sadd(f'engagement:intcon:out:{route}', nameid)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_routing_table, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.put("/libreapi/routing/table/{identifier}", status_code=200)
def update_routing_table(reqbody: RoutingTableModel, response: Response, identifier: str=Path(..., regex=_NAME_)):
    result = None
    try:
        pipe = rdbconn.pipeline()
        name = reqbody.name
        _nameid = f'table:{identifier}'; _name_key = f'routing:{_nameid}'
        nameid = f'table:{name}'; name_key = f'routing:{nameid}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent routing table identifier'}; return
        if name != identifier:
            if rdbconn.exists(name_key):
                response.status_code, result = 403, {'error': 'existent routing table name'}; return
            else:
               response.status_code, result = 403, {'error': 'change name routing table is not allowed'}; return

        # get current data
        _data = jsonhash(rdbconn.hgetall(_name_key))
        _routes = _data.get('routes')
        # transaction block
        pipe.multi()
        if _routes:
            for _route in _routes[:2]:
                pipe.srem(f'engagement:intcon:out:{_route}', _nameid)

        data = jsonable_encoder(reqbody)
        pipe.hmset(name_key, redishash(data))
        routes = data.get('routes')
        if routes:
            for route in _routes[:2]:
                pipe.sadd(f'engagement:intcon:out:{route}', nameid)
        # remove unintended field
        for field in _data:
            if field not in data:
                pipe.hdel(name_key, field)

        if name != identifier:
            _engaged_key = f'engagement:{_name_key}'
            engaged_key = f'engagement:{name_key}'
            engagements = rdbconn.smembers(_engaged_key)
            for engagement in engagements:
                pipe.hset(f'intcon:{engagement}', 'routing', name)
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

@librerouter.delete("/libreapi/routing/table/{identifier}", status_code=200)
def delete_routing_table(response: Response, identifier: str=Path(..., regex=_NAME_)):
    result = None
    try:
        pipe = rdbconn.pipeline()
        _nameid = f'table:{identifier}'; _name_key = f'routing:{_nameid}'
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
        # get current data
        _routes = fieldjsonify(rdbconn.hget(_name_key, 'routes'))
        if _routes:
            for _route in _routes[:2]:
                pipe.srem(f'engagement:intcon:out:{_route}', _nameid)
        pipe.delete(_engaged_key)
        pipe.delete(_name_key)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=delete_routing_table, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libreapi/routing/table/{identifier}", status_code=200)
def detail_routing_table(response: Response, identifier: str=Path(..., regex=_NAME_)):
    result = None
    try:
        _name_key = f'routing:table:{identifier}'
        _engaged_key = f'engagement:{_name_key}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent routing table identifier'}; return
        data = jsonhash(rdbconn.hgetall(_name_key))
        _routes = data.get('routes')
        if _routes:
            data['routes'] = {'primary': _routes[0], 'secondary': _routes[1], 'load': int(_routes[2])}

        # get records
        pipe = rdbconn.pipeline()
        KEYPATTERN = f'routing:record:{identifier}:*'
        next, mainkeys = rdbconn.scan(0, KEYPATTERN, SCAN_COUNT)
        while next:
            next, tmpkeys = rdbconn.scan(next, KEYPATTERN, SCAN_COUNT)
            mainkeys += tmpkeys

        for mainkey in mainkeys:
            if mainkey.endswith(':compare:'): pipe.hgetall(mainkey)
            else: pipe.get(mainkey)
        details = pipe.execute()
        records = list()
        for mainkey, detail in zip(mainkeys, details):
            _, _, _, match, value = listify(mainkey)
            if value==__EMPTY_STRING__: value = __DEFAULT_ENTRY__
            if match=='compare':
                for hashfield, valuefield in detail.items():
                    compare, param = listify(hashfield)
                    recordvalue = listify(valuefield)
                    action = recordvalue[0]
                    record = {'matching': compare, 'value': param, 'action': action}
                    if action != 'block':
                        record.update({'routes':{'primary': recordvalue[1], 'secondary': recordvalue[2], 'load': int(recordvalue[3])}})
                    records.append(record)
            else:
                splitdetail = listify(detail)
                action = splitdetail[0]
                record = {'match': match, 'value': value, 'action': action}
                if action != _BLOCK:
                    record.update({'routes': {'primary': splitdetail[1], 'secondary': splitdetail[2], 'load': int(splitdetail[3])}})
                records.append(record)
        engagements = rdbconn.smembers(_engaged_key)
        data.update({'records': records, 'engagements': engagements})
        response.status_code, result = 200, data
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=detail_routing_table, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libreapi/routing/table", status_code=200)
def list_routing_table(response: Response):
    result = None
    try:
        pipe = rdbconn.pipeline()
        KEYPATTERN = f'routing:table:*'
        next, mainkeys = rdbconn.scan(0, KEYPATTERN, SCAN_COUNT)
        while next:
            next, tmpkeys = rdbconn.scan(next, KEYPATTERN, SCAN_COUNT)
            mainkeys += tmpkeys

        for mainkey in mainkeys: pipe.hgetall(mainkey)
        details = pipe.execute()

        data = list()
        for mainkey, detail in zip(mainkeys, details):
            detail = jsonhash(detail)
            routes = detail.get('route')
            if routes:
                detail['routes'] = {'primary': routes[0], 'secondary': routes[1], 'load': int(routes[2])}
            data.append(detail)
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
    eq = 'eq'
    ne = 'ne'
    gt = 'gt'
    lt = 'lt'

_COMPARESET = {'eq', 'ne', 'gt', 'lt'}

class RoutingRecordActionEnum(str, Enum):
    route = _ROUTE
    block = _BLOCK
    jumps = _JUMPS

class RoutingRecordModel(BaseModel):
    table: str = Field(regex=_NAME_, max_length=32, description='name of routing table')
    match: MatchingEnum = Field(description='matching options, include lpm: longest prefix match, em: exact match, eq: equal, ne: not equal, gt: greater than, lt: less than',)
    value: str = Field(min_length=1, max_length=128, regex=_DIAL_, description=f'value of variable that declared in routing table. {__DEFAULT_ENTRY__} is predefined value for default entry')
    action: RoutingRecordActionEnum = Field(default=_ROUTE, description=f'routing action: {_JUMPS} - jumps to other routing table; {_BLOCK} - block the call; {_ROUTE} - route call to outbound interconnection')
    routes: Optional[RouteModel] = Field(description='route model data')
    # validation and transform data
    @root_validator()
    def routing_record_agreement(cls, values):
        #try:
        values = jsonable_encoder(values)
        table = values.get('table')
        action = values.pop('action')
        if not rdbconn.exists(f'routing:table:{table}'):
            raise ValueError('nonexistent routing table')

        if action==_BLOCK:
            values.pop('routes', None)
        if action in [_JUMPS, _ROUTE]:
            routes = values.get('routes')
            if not routes:
                raise ValueError(f'routes parameter is required for {action} action')
            else:
                primary = routes.get('primary')
                secondary = routes.get('secondary')
                load = routes.get('load')
                if action == _ROUTE:
                    for intconname in [primary, secondary]:
                        if not rdbconn.exists(f'intcon:out:{intconname}'):
                            raise ValueError('nonexistent outbound interconnect')
                else:
                    for _table in [primary, secondary]:
                        if _table == table:
                            raise ValueError(f'routing loop to itself')
                        if not rdbconn.exists(f'routing:table:{_table}'):
                            raise ValueError('nonexistent routing table')
                values['routes'] = [action, primary, secondary, load]
        return values


@librerouter.post("/libreapi/routing/record", status_code=200)
def create_routing_record(reqbody: RoutingRecordModel, response: Response):
    result = None
    try:
        pipe = rdbconn.pipeline()
        data = jsonable_encoder(reqbody)
        table = data.get('table')
        match = data.get('match')
        value = data.get('value')
        if value == __DEFAULT_ENTRY__: value = __EMPTY_STRING__
        routes = data.get('routes')

        nameid = f'record:{table}:{match}:{value}'
        hashfield = None
        if match in _COMPARESET:
            record_key = f'routing:record:{table}:compare:'
            hashfield = f'{match}:{value}'
            if rdbconn.hexists(record_key, hashfield):
                response.status_code, result = 403, {'error': 'existent routing record'}; return
        else:
            record_key = f'routing:{nameid}'
            if rdbconn.exists(record_key):
                response.status_code, result = 403, {'error': 'existent routing record'}; return

        action = routes[0]
        if action==_ROUTE:
            for route in routes[1:3]:
                pipe.sadd(f'engagement:intcon:out:{route}', nameid)
        elif action==_JUMPS:
            for route in routes[1:3]:
                pipe.sadd(f'engagement:routing:table:{route}', nameid)

        if hashfield: pipe.hset(record_key, hashfield, stringify(map(str, routes)))
        else: pipe.set(record_key, stringify(map(str, routes)))
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_routing_record, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


@librerouter.put("/libreapi/routing/record", status_code=200)
def update_routing_record(reqbody: RoutingRecordModel, response: Response):
    result = None
    try:
        pipe = rdbconn.pipeline()
        data = jsonable_encoder(reqbody)
        table = data.get('table')
        match = data.get('match')
        value = data.get('value')
        if value == __DEFAULT_ENTRY__: value = __EMPTY_STRING__

        nameid = f'record:{table}:{match}:{value}'
        hashfield = None
        if match in _COMPARESET:
            record_key = f'routing:record:{table}:compare:'
            hashfield = f'{match}:{value}'
            if not rdbconn.hexists(record_key, hashfield):
                response.status_code, result = 403, {'error': 'non existent routing record'}; return
        else:
            record_key = f'routing:{nameid}'
            if not rdbconn.exists(record_key):
                response.status_code, result = 403, {'error': 'non existent routing record'}; return

        # process old data
        if hashfield: _routes = listify(rdbconn.hget(record_key, hashfield))
        else: _routes = listify(rdbconn.get(record_key))
        _action = _routes[0]
        if _action==_ROUTE:
            for _route in _routes[1:3]:
                pipe.srem(f'engagement:intcon:out:{_route}', nameid)
        elif _action==_JUMPS:
            for _route in _routes[1:3]:
                pipe.srem(f'engagement:routing:table:{_route}', nameid)
        else: pass
        # process new data
        routes = data.get('routes')
        action = routes[0]
        if action==_ROUTE:
            for route in routes[1:3]:
                pipe.sadd(f'engagement:intcon:out:{route}', nameid)
        elif action==_JUMPS:
            for route in routes[1:3]:
                pipe.sadd(f'engagement:routing:table:{route}', nameid)
        else: pass

        if hashfield: pipe.hset(record_key, hashfield, stringify(map(str, routes)))
        else: pipe.set(record_key, stringify(map(str, routes)))
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=update_routing_record, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


@librerouter.delete("/libreapi/routing/record/{table}/{match}/{value}", status_code=200)
def delete_routing_record(response: Response, value:str=Path(..., regex=_DIAL_), table:str=Path(..., regex=_NAME_),
                          match:str=Path(..., regex='^(em|lpm|eq|ne|gt|lt)$')):
    result = None
    try:
        pipe = rdbconn.pipeline()
        if value == __DEFAULT_ENTRY__: value = __EMPTY_STRING__

        nameid = f'record:{table}:{match}:{value}'
        hashfield = None
        if match in _COMPARESET:
            record_key = f'routing:record:{table}:compare:'
            hashfield = f'{match}:{value}'
            if not rdbconn.hexists(record_key, hashfield):
                response.status_code, result = 403, {'error': 'non existent routing record'}; return
        else:
            record_key = f'routing:{nameid}'
            if not rdbconn.exists(record_key):
                response.status_code, result = 403, {'error': 'non existent routing record'}; return

        if hashfield: _routes = listify(rdbconn.hget(record_key, hashfield))
        else: _routes = listify(rdbconn.get(record_key))
        _action = _routes[0]
        if _action==_ROUTE:
            for _route in _routes[1:3]:
                pipe.srem(f'engagement:intcon:out:{_route}', nameid)
        if _action==_JUMPS:
            for _route in _routes[1:3]:
                pipe.srem(f'engagement:routing:table:{_route}', nameid)

        if hashfield: pipe.hdel(record_key, hashfield)
        else:  pipe.delete(record_key)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=delete_routing_record, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ACCESS SERVICE
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------

class Socket(BaseModel):
    transport: TransportEnum = Field(default='udp', description='transport protocol', hidden_field=True)
    port: int = Field(default=5060, ge=0, le=65535, description='sip port', hidden_field=True )
    ip: IPv4Address = Field(description='ip address')
    force: Optional[bool] = Field(description='set true if you need to add none loopback ip', hidden_field=True)
    @root_validator()
    def socket_ip(cls, kvs):
        kvs = jsonable_encoder(kvs)
        force = kvs.pop('force', None)
        if not force:
            ip = kvs.get('ip')
            if not IPv4Network(ip).is_loopback:
                raise ValueError('ip must be loopback address only')
        return kvs

class DomainPolicy(BaseModel):
    domain: str = Field(regex=_REALM_, max_length=32, description='sip domain')
    srcsocket: Socket = Field(description='listen socket of sip between proxy and b2bua')
    dstsocket: Socket = Field(description='forward socket of sip between proxy and b2bua')
    @root_validator()
    def policy(cls, kvs):
        kvs = jsonable_encoder(kvs)
        domain = kvs.get('domain')
        if not validators.domain(domain):
            raise ValueError('Invalid domain name, please refer rfc1035')
        src_socket = kvs.get('srcsocket')
        srcsocket = f'{src_socket["transport"]}:{src_socket["ip"]}:{src_socket["port"]}'
        dst_socket = kvs.get('dstsocket')
        dstsocket = f'{dst_socket["transport"]}:{dst_socket["ip"]}:{dst_socket["port"]}'
        if dstsocket == srcsocket:
            raise ValueError('source and destination sockets are same')
        kvs.update({'srcsocket': srcsocket, 'dstsocket': dstsocket})
        return kvs

@librerouter.post("/libreapi/access/domain-policy", status_code=200)
def create_access_domain_policy(reqbody: DomainPolicy, response: Response):
    requestid=get_request_uuid()
    result = None
    try:
        data = jsonable_encoder(reqbody)
        domain = data.pop('domain')
        # verification
        name_key = f'access:policy:{domain}'
        if rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent access policy domain'}; return
        rdbconn.hmset(name_key, data)
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_access_domain_policy, requestid={requestid}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


@librerouter.patch("/libreapi/access/domain-policy", status_code=200)
def update_access_domain_policy(reqbody: DomainPolicy, response: Response):
    requestid=get_request_uuid()
    result = None
    try:
        data = jsonable_encoder(reqbody)
        domain = data.pop('domain')
        # verification
        name_key = f'access:policy:{domain}'
        _engage_key = f'engagement:{name_key}'
        if not rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'nonexistent access policy domain'}; return
        rdbconn.hmset(name_key, data)
        response.status_code, result = 200, {'passed': True}

        layer = rdbconn.srandmember(_engage_key)
        if layer:
            rdbconn.publish(CHANGE_CFG_CHANNEL, json.dumps({'portion': 'policy:domain', 'action': 'update', 'layer': layer, 'requestid': requestid}))
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=update_access_domain_policy, requestid={requestid}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


@librerouter.delete("/libreapi/access/domain-policy/{domain}", status_code=200)
def delete_access_domain_policy(response: Response, domain:str=Path(..., regex=_REALM_)):
    requestid=get_request_uuid()
    result = None
    try:
        _name_key = f'access:policy:{domain}'
        _engage_key = f'engagement:{_name_key}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent access policy domain'}; return
        if rdbconn.scard(_engage_key):
            response.status_code, result = 403, {'error': 'engaged access policy domain'}; return

        # check if routing records exists in table
        _DIRECTORY_KEY_PATTERN = f'access:dir:*:{domain}:*'
        next, records = rdbconn.scan(0, _DIRECTORY_KEY_PATTERN, SCAN_COUNT)
        if records:
            response.status_code, result = 400, {'error': 'domain policy in used'}; return
        else:
            while next:
                next, records = rdbconn.scan(next, _DIRECTORY_KEY_PATTERN, SCAN_COUNT)
                if records:
                    response.status_code, result = 400, {'error': 'domain policy in used'}; return

        pipe = rdbconn.pipeline()
        pipe.delete(_name_key)
        pipe.delete(_engage_key)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=delete_access_domain_policy, requestid={requestid}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


@librerouter.get("/libreapi/access/domain-policy/{domain}", status_code=200)
def detail_access_domain_policy(response: Response, domain:str=Path(..., regex=_REALM_)):
    result = None
    try:
        _name_key = f'access:policy:{domain}'
        _engage_key = f'engagement:{_name_key}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent access policy domain'}; return
        data = rdbconn.hgetall(_name_key)
        src_socket = listify(data.get('srcsocket'))
        srcsocket = {'transport': src_socket[0], 'ip': src_socket[1], 'port': src_socket[2]}
        dst_socket = listify(data.get('dstsocket'))
        dstsocket = {'transport': dst_socket[0], 'ip': dst_socket[1], 'port': dst_socket[2]}
        engagements = rdbconn.smembers(_engage_key)
        result = {'domain': domain, 'srcsocket': srcsocket, 'dstsocket': dstsocket, 'engagements': engagements}
        response.status_code = 200
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=detail_access_domain_policy, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


@librerouter.get("/libreapi/access/domain-policy", status_code=200)
def list_access_domain_policy(response: Response):
    result = None
    try:
        pipe = rdbconn.pipeline()
        KEYPATTERN = f'access:policy:*'
        next, mainkeys = rdbconn.scan(0, KEYPATTERN, SCAN_COUNT)
        while next:
            next, tmpkeys = rdbconn.scan(next, KEYPATTERN, SCAN_COUNT)
            mainkeys += tmpkeys
        result = [getaname(mainkey) for mainkey in mainkeys]
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=list_access_domain_policy, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------

class AntiFlooding(BaseModel):
    sampling: int = Field(default=2, ge=1, le=300, description='sampling time unit (in second)')
    density: int = Field(default=20, ge=1, le=3000, description='number of request that allow in sampling time, then will be ignore within window time')
    window: int = Field(default=600, ge=300, le=1200, description='evaluated window time in second')
    threshold: int = Field(default=10, ge=1, le=3600, description='number of failure threshold that will be banned')
    bantime: int = Field(default=600, ge=600, le=864000, description='firewall ban time in second')

class AuthFailure(BaseModel):
    window: int = Field(default=600, ge=300, le=1200, description='evaluated window time in second')
    threshold: int = Field(default=10, ge=1, le=3600, description='number of authentication failure threshold that will be banned')
    bantime: int = Field(default=900, ge=600, le=864000, description='firewall ban time in second')

class AttackAvoid(BaseModel):
    window: int = Field(default=18000, ge=3600, le=86400, description='evaluated window time in second')
    threshold: int = Field(default=5, ge=1, le=3600, description='number of request threshold that will be banned')
    bantime: int = Field(default=86400, ge=600, le=864000, description='firewall ban time in second')

class AccessService(BaseModel):
    name: str = Field(regex=_NAME_, max_length=32, description='name of access service')
    desc: Optional[str] = Field(default='access service', max_length=64, description='description')
    server_header: Optional[str] = Field(max_length=64, description='Server Header')
    trying_reason: str = Field(default='Trying', max_length=64, description='Trying Reason', hidden_field=True)
    natping_from: str = Field(default='sip:keepalive@libre.sbc', max_length=64, description='natping from', hidden_field=True)
    transports: List[TransportEnum] = Field(default=['udp', 'tcp'], min_items=1, max_items=3, description='list of bind transport protocol')
    sip_address: str = Field(description='IP address via NetAlias use for SIP Signalling')
    sip_port: int = Field(default=5060, ge=0, le=65535, description='sip port', hidden_field=True)
    sips_port: int = Field(default=5061, ge=0, le=65535, description='sip tls port', hidden_field=True)
    topology_hiding: Optional[str] = Field(description='topology hiding, you should never need to use', hidden_field=True)
    antiflooding: Optional[AntiFlooding] = Field(description='antifloofing/ddos')
    authfailure: AuthFailure = Field(description='authentication failure/bruteforce/intrusion detection')
    attackavoid: AttackAvoid = Field(description='attack avoidance')
    blackips: List[IPv4Network] = Field(default=[], max_items=1024, description='denied ip list')
    whiteips: List[IPv4Network] = Field(default=[], max_items=1024 ,description='allowed ip list')
    domains: List[str] = Field(min_items=1, max_items=8, description='list of policy domain')
    @root_validator
    def access_service_validation(cls, kvs):
        kvs = jsonable_encoder(kvs)
        domains = kvs.get('domains')
        for domain in domains:
            if not validators.domain(domain):
                raise ValueError('Invalid domain name, please refer rfc1035')
            if not rdbconn.exists(f'access:policy:{domain}'):
                raise ValueError('Undefined domain')
        sip_address = kvs.get('sip_address')
        if not rdbconn.exists(f'base:netalias:{sip_address}'):
            raise ValueError('nonexistent network alias')
        topology_hiding = kvs.pop('topology_hiding', None)
        if topology_hiding: kvs['topology_hiding'] = topology_hiding
        blackips = kvs.get('blackips')
        whiteips = kvs.get('whiteips')
        if blackips and whiteips:
            raise ValueError('only one of blackips/whiteips can be set')
        return kvs


@librerouter.post("/libreapi/access/service", status_code=200)
def create_access_service(reqbody: AccessService, response: Response):
    requestid=get_request_uuid()
    result = None
    try:
        pipe = rdbconn.pipeline()
        data = jsonable_encoder(reqbody)
        name = data.get('name')
        domains = data.get('domains')
        sip_address = data.get('sip_address')
        # verification
        name_key = f'access:service:{name}'
        if rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent access layer'}; return

        domain_engaged_prefix = 'engagement:access:policy'
        for domain in domains:
            if rdbconn.srandmember(f'{domain_engaged_prefix}:{domain}'):
                response.status_code, result = 403, {'error': 'domain is used by other access service layer'}; return
        pipe.hmset(name_key, redishash(data))
        pipe.sadd('nameset:access:service', name)
        for domain in domains:
            pipe.sadd(f'{domain_engaged_prefix}:{domain}', name)
        pipe.sadd(f'engagement:base:netalias:{sip_address}', name_key)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
        # fire-event inbound interconnect create
        rdbconn.publish(CHANGE_CFG_CHANNEL, json.dumps({'portion': 'access:service', 'action': 'create', 'name': name, 'requestid': requestid}))
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_access_service, requestid={requestid}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.put("/libreapi/access/service/{identifier}", status_code=200)
def update_access_service(reqbody: AccessService, response: Response, identifier: str=Path(..., regex=_NAME_)):
    requestid=get_request_uuid()
    result = None
    try:
        pipe = rdbconn.pipeline()
        data = jsonable_encoder(reqbody)
        name = data.get('name')
        domains = data.get('domains')
        sip_address = data.get('sip_address')
        # verification
        name_key = f'access:service:{name}'
        _name_key = f'access:service:{identifier}'

        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent access layer'}; return
        if name != identifier and rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent class name'}; return

        domain_engaged_prefix = 'engagement:access:policy'
        for domain in domains:
            layer = rdbconn.srandmember(f'{domain_engaged_prefix}:{domain}')
            if layer and layer != identifier:
                response.status_code, result = 403, {'error': 'domain is used by other access service layer'}; return

        _data = jsonhash(rdbconn.hgetall(_name_key))
        _domains = _data.get('domains')
        _sip_address = _data.get('sip_address')
        for _domain in _domains:
            pipe.srem(f'{domain_engaged_prefix}:{_domain}', identifier)
        pipe.srem(f'engagement:base:netalias:{_sip_address}', _name_key)
        pipe.srem(f'nameset:access:service', identifier)
        pipe.sadd(f'nameset:access:service', name)
        pipe.hmset(name_key, redishash(data))
        for domain in domains:
            pipe.sadd(f'{domain_engaged_prefix}:{domain}', name)
        pipe.sadd(f'engagement:base:netalias:{sip_address}', name_key)
        # remove the unintended-field
        for _field in _data:
            if _field not in data:
                pipe.hdel(_name_key, _field)
        if name != identifier:
            pipe.delete(_name_key)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
        # fire-event inbound interconnect create
        rdbconn.publish(CHANGE_CFG_CHANNEL, json.dumps({'portion': 'access:service', 'action': 'update', 'name': name, '_name': identifier, 'requestid': requestid}))
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=update_access_service, requestid={requestid}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


@librerouter.delete("/libreapi/access/service/{identifier}", status_code=200)
def delete_access_service(response: Response, identifier: str=Path(..., regex=_NAME_)):
    result = None
    requestid = get_request_uuid()
    try:
        _name_key = f'access:service:{identifier}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent access layer'}; return

        _domains = listify(rdbconn.hget(_name_key, 'domains'))
        pipe = rdbconn.pipeline()
        for _domain in _domains:
            pipe.srem(f'engagement:access:policy:{_domain}', identifier)
        _sip_address = rdbconn.hget(_name_key, 'sip_address')
        pipe.srem(f'engagement:base:netalias:{_sip_address}', _name_key)
        pipe.srem(f'nameset:access:service', identifier)
        pipe.delete(_name_key)
        pipe.execute()
        response.status_code, result = 200, {'passed': True}
        # fire-event inbound interconnect create
        rdbconn.publish(CHANGE_CFG_CHANNEL, json.dumps({'portion': 'access:service', 'action': 'delete', '_name': identifier, 'requestid': requestid}))
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=delete_access_service, requestid={requestid}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


@librerouter.get("/libreapi/access/service/{identifier}", status_code=200)
def detail_access_service(response: Response, identifier: str=Path(..., regex=_NAME_)):
    requestid=get_request_uuid()
    result = None
    try:
        _name_key = f'access:service:{identifier}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent access layer'}; return
        result = jsonhash(rdbconn.hgetall(_name_key))
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=detail_access_service, requestid={requestid}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libreapi/access/service", status_code=200)
def list_access_service(response: Response):
    result = None
    try:
        pipe = rdbconn.pipeline()
        KEYPATTERN = f'access:service:*'
        next, mainkeys = rdbconn.scan(0, KEYPATTERN, SCAN_COUNT)
        while next:
            next, tmpkeys = rdbconn.scan(next, KEYPATTERN, SCAN_COUNT)
            mainkeys += tmpkeys

        for mainkey in mainkeys:
            pipe.hget(mainkey, 'desc')
        descriptions = pipe.execute()

        data = list()
        for mainkey, description in zip(mainkeys, descriptions):
            data.append({'name': getaname(mainkey), 'desc': description})

        response.status_code, result = 200, data
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=list_access_service, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
class NetDirectory(BaseModel):
    domain: str = Field(description='user domain')
    ip: IPv4Network = Field(description='IPv4 Address for IP auth')
    port: int = Field(default=5060, ge=0, le=65535, description='farend destination port for arriving call')
    transport: TransportEnum = Field(default='udp', description='farend transport protocol for arriving call')


class UserDirectory(BaseModel):
    domain: str = Field(description='user domain')
    id: str = Field(regex=_NAME_, max_length=16, description='user identifier')
    secret: str = Field(min_length=8, max_length=32, description='password of digest auth for inbound')
    @root_validator
    def user_directory_validation(cls, kvs):
        domain = kvs.get('domain')
        if not validators.domain(domain):
            raise ValueError('Invalid domain name, please refer rfc1035')
        if not rdbconn.exists(f'access:policy:{domain}'):
            raise ValueError('Undefined domain')
        return kvs


@librerouter.post("/libreapi/access/directory/user", status_code=200)
def create_access_directory_user(reqbody: UserDirectory, response: Response):
    result = None
    try:
        data = jsonable_encoder(reqbody)
        domain = data.get('domain')
        id = data.get('id')
        name_key = f'access:dir:usr:{domain}:{id}'
        if rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'existent user'}; return
        secret = data.get('secret')
        rdbconn.hmset(name_key, {'secret': secret, 'a1hash': hashlib.md5(f'{id}:{domain}:{secret}'.encode()).hexdigest()})
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=create_access_directory_user, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.patch("/libreapi/access/directory/user", status_code=200)
def update_access_directory_user(reqbody: UserDirectory, response: Response):
    result = None
    try:
        data = jsonable_encoder(reqbody)
        domain = data.get('domain')
        id = data.get('id')
        name_key = f'access:dir:usr:{domain}:{id}'
        if not rdbconn.exists(name_key):
            response.status_code, result = 403, {'error': 'nonexistent user'}; return
        secret = data.get('secret')
        rdbconn.hmset(name_key, {'secret': secret, 'a1hash': hashlib.md5(f'{id}:{domain}:{secret}'.encode()).hexdigest()})
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=update_access_directory_user, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.delete("/libreapi/access/directory/user/{domain}/{id}", status_code=200)
def delete_access_directory_user(response: Response, domain: str=Path(..., regex=_REALM_), id:str=Path(..., regex=_NAME_)):
    result = None
    try:
        _name_key = f'access:dir:usr:{domain}:{id}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent user'}; return
        rdbconn.delete(_name_key)
        response.status_code, result = 200, {'passed': True}
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=delete_access_directory_user, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libreapi/access/directory/user/{domain}/{id}", status_code=200)
def detail_access_directory_user(response: Response, domain: str=Path(..., regex=_REALM_), id:str=Path(..., regex=_NAME_)):
    result = None
    try:
        _name_key = f'access:dir:usr:{domain}:{id}'
        if not rdbconn.exists(_name_key):
            response.status_code, result = 403, {'error': 'nonexistent user'}; return
        result = rdbconn.hgetall(_name_key)
        response.status_code = 200
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=detail_access_directory_user, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

@librerouter.get("/libreapi/access/directory/user/{domain}", status_code=200)
def list_access_directory_user(response: Response, domain: str=Path(..., regex=r'^[a-z][a-z0-9_\-\.]+$|^\*$')):
    result = None
    try:
        pipe = rdbconn.pipeline()
        KEYPATTERN = f'access:dir:usr:{domain}:*'
        next, mainkeys = rdbconn.scan(0, KEYPATTERN, SCAN_COUNT)
        while next:
            next, tmpkeys = rdbconn.scan(next, KEYPATTERN, SCAN_COUNT)
            mainkeys += tmpkeys

        data = {}
        for mainkey in mainkeys:
            _, _, _, domain, id = listify(mainkey)
            if domain in data: data[domain].append(id)
            else: data[domain] = [id]

        response.status_code, result = 200, data
    except Exception as e:
        response.status_code, result = 500, None
        logify(f"module=liberator, space=libreapi, action=list_access_directory_user, requestid={get_request_uuid()}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result
