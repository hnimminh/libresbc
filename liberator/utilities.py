import syslog
from uuid import uuid4
from hashlib import md5
from contextvars import ContextVar

from hrid import HRID

# delimiter for data transformation
_delimiter_ = ','
# distinct request uuid for log tracing
_request_uuid_ctx_var: ContextVar[str] = ContextVar('request_uuid', default=None)
def get_request_uuid() -> str:
    return _request_uuid_ctx_var.get()

# human readable identifier
humanrid = HRID(delimeter='-', hridfmt=('adjective', 'noun'))

def logify(msg):
    syslog.openlog('libresbc', syslog.LOG_PID, syslog.LOG_LOCAL7)
    syslog.syslog(syslog.LOG_INFO, msg)

def debugy(msg):
    syslog.openlog('libresbc', syslog.LOG_PID, syslog.LOG_LOCAL7)
    syslog.syslog(syslog.LOG_DEBUG, msg)

def int2bool(number):
    number = int(number)
    return True if number else False

def bool2int(booleaner):
    assert type(booleaner) == bool
    return 1 if booleaner else 0

def rembytes(data):
    if isinstance(data, bytes):       return data.decode()
    if isinstance(data, (str,int)):   return data
    if isinstance(data, dict):        return dict(map(rembytes, data.items()))
    if isinstance(data, tuple):       return tuple(map(rembytes, data))
    if isinstance(data, list):        return list(map(rembytes, data))
    if isinstance(data, set):         return set(map(rembytes, data))


def redishash(data: dict) -> dict:
    if isinstance(data, dict):
        for key in list(data):
            value = data.get(key)
            if isinstance(value, bool):
                if value: data.update({key: ':bool:true'})
                else: data.update({key: ':bool:false'})
            elif isinstance(value, int): data.update({key: f':int:{value}'})
            if isinstance(value, (list,set)): data.update({key: f':list:{_delimiter_.join(value)}'})
            if value is None: data.pop(key)
    return data


def jsonhash(data: dict) -> dict:
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str):
                if value == ':bool:true': data.update({key: True})
                if value == ':bool:false': data.update({key: False})
                if value.startswith(':int:'): data.update({key: int(value[5:])}) 
                if value.startswith(':list:'): data.update({key: value[6:].split(_delimiter_)})
    return data
