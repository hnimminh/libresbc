import time
import traceback
import random
import json
from threading import Thread

import redis
import greenswitch  

from configuration import (NODEID, ESL_HOST, ESL_PORT, ESL_SECRET, 
                           REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD, REDIS_TIMEOUT)
from utilities import logify, debugy

REDIS_CONNECTION_POOL = redis.BlockingConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD, 
                                                     decode_responses=True, max_connections=5, timeout=5)

def fssocket(command):
    try:
        fs = greenswitch.InboundESL(host=ESL_HOST, port=ESL_PORT, password=ESL_SECRET)
        fs.connect()
        result = fs.send(f'api {command}')
        if result:
            print(result.data)
    except Exception as e:
        logify(f"module=liberator, space=bases, action=fssocket, command={command}, exception={e}, tracings={traceback.format_exc()}")
    finally:
        pass    

def netfilter():
    pass



class BaseEventHandler(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.stop = False
        self.daemon = True
        self.setName('BaseEventHandler')

    def run(self):
        logify(f"module=liberator, space=bases, action=start_base_event_handler_thread")
        rdbconn = redis.StrictRedis(connection_pool=REDIS_CONNECTION_POOL)
        while not self.stop:
            events = list()
            try:
                intcon_api_event = f'event:api:peer:{NODEID}'

                events = rdbconn.blpop([intcon_api_event], REDIS_TIMEOUT)
                if events:
                    eventkey, eventvalue = events[0], json.loads(events[1])
                    logify(f"module=liberator, space=bases, action=catch_event, eventkey={eventkey}, eventvalue={eventvalue}")
                    if eventkey in [intcon_api_event]:
                        subevent = eventvalue.get('subevent')
                        prewait = eventvalue.get('prewait')
                        requestid = eventvalue.get('requestid')
                        data = eventvalue.get('data')
                        # make the node run this task in different timestamp
                        time.sleep(int(prewait))
                    else:
                        pass
            except Exception as e:
                logify(f"module=liberator, space=bases, class=BaseEventHandler, action=run, events={events}, exception={e}, tracings={traceback.format_exc()}")
                time.sleep(5)
            finally:
                pass
