import time
import traceback
import random
import json
from threading import Thread

import redis
import ESL

from configuration import (CES_HOST, CES_PORT, CES_SECRET, 
                           REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD, REDIS_TIMEOUT)
from utilities import logify, debugy

REDIS_CONNECTION_POOL = redis.BlockingConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD, 
                                                     decode_responses=True, max_connections=5, timeout=5)

def fssocket(command):
    result, error = None, None
    con = ESL.ESLconnection(CES_HOST, CES_PORT, CES_SECRET)
    if con.connected(): result = con.api(command)
    else: error = 'Call Engine is not ready'
    return result, error


def firewall():
    # This library is implemented in pure-python and does not interface with C library libiptc 
    # using libiptc directly is not recommended by netfilter development team
    # http://www.netfilter.org/documentation/FAQ/netfilter-faq-4.html#ss4.5
    # thus eliminating a number of issues arising from interface changes while staying compatible with different versions of iptables.
    pass



class EventControl(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.stop = False
        self.daemon = True
        self.setName('EventControl')

    def run(self):
        rdbconn = redis.StrictRedis(connection_pool=REDIS_CONNECTION_POOL) 
        while not self.stop:
            events = rdbconn.blpop('event', REDIS_TIMEOUT)
            try:
                pass
            except Exception as e:
                logify(f"module=liberator, space=callenginectl, exception={e}")  
            finally:
                pass