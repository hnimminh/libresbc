import syslog
from threading import Thread
from uuid import uuid4
from hashlib import md5
from contextvars import ContextVar

# delimiter for data transformation
_delimiter_ = ','
# distinct request uuid for log tracing
_request_uuid_ctx_var: ContextVar[str] = ContextVar('request_uuid', default=None)
def get_request_uuid() -> str:
    return _request_uuid_ctx_var.get()

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


def fieldredisify(data):
    if isinstance(data, bool):
        if data: return ':bool:true'
        else: return ':bool:false'
    elif isinstance(data, int): return f':int:{data}'
    elif isinstance(data, float): return f':float:{data}'
    elif isinstance(data, (list,set)): 
        try: return f':list:{_delimiter_.join(data)}'
        except: return f':list:{_delimiter_.join([str(i) for i in data])}'
    elif data is None: return ':none:'
    else: return data


def redishash(data: dict) -> dict:
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, bool):
                if value: data.update({key: ':bool:true'})
                else: data.update({key: ':bool:false'})
            elif isinstance(value, int): data.update({key: f':int:{value}'})
            elif isinstance(value, float): data.update({key: f':float:{value}'})
            elif isinstance(value, (list,set)): 
                try: data.update({key: f':list:{_delimiter_.join(value)}'})
                except: data.update({key: f':list:{_delimiter_.join([str(v) for v in value])}'})
            elif value is None: data.update({key: ':none:'})
            else: pass
    return data


def fieldjsonify(data):
    if isinstance(data, str):
        if data.startswith(':bool:'):
            if data == ':bool:true': return True
            if data == ':bool:false': return False
        elif data.startswith(':int:'): return int(data[5:]) 
        elif data.startswith(':float:'): return float(data[7:])
        elif data.startswith(':list:'): 
            if data==':list:': return []
            else:
                _data = data[6:].split(_delimiter_)
                try: return [int(v) for v in _data]
                except: return _data
        elif data.startswith(':none:'): return None
        else: return data
    else: return data


def jsonhash(data: dict) -> dict:
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str):
                if value.startswith(':bool:'):
                    if value == ':bool:true': data.update({key: True})
                    if value == ':bool:false': data.update({key: False})
                elif value.startswith(':int:'): data.update({key: int(value[5:])}) 
                elif value.startswith(':float:'): data.update({key: float(value[7:])}) 
                elif value.startswith(':list:'): 
                    if value==':list:': data.update({key: []})
                    else:
                        _value = value[6:].split(_delimiter_)
                        try: data.update({key: [int(v) for v in _value]})
                        except: data.update({key: _value})
                elif value.startswith(':none:'): data.update({key: None})
                else: pass
    return data

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def listify(string, delimiter=':') -> list:
    assert isinstance(string, str)
    return string.split(delimiter)

def getnameid(string) -> str:
    array = string.split(':')
    if array[-1].startswith('_'): return array[-2]
    else: return array[-1]

def threaded(func, *params):
    th = Thread(target=func, args=params)
    th.start()
