import syslog
from uuid import uuid4
from hashlib import md5
from contextvars import ContextVar

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

def rembytes (data):
  if isinstance(data, bytes):       return data.decode()
  if isinstance(data, (str,int)):   return data
  if isinstance(data, dict):        return dict(map(rembytes, data.items()))
  if isinstance(data, tuple):       return tuple(map(rembytes, data))
  if isinstance(data, list):        return list(map(rembytes, data))
  if isinstance(data, set):         return set(map(rembytes, data))

def nameid(name):
    return md5(f'{name}'.lower().encode()).hexdigest()

def guid() -> str: 
    return str(uuid4())
