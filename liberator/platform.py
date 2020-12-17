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
    con = ESL.ESLconnection(CES_HOST, CES_PORT, CES_SECRET)
    if con.connected():
        return con.api(command)
    else:
        return None

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