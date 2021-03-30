import time
import traceback
import random
import json
from threading import Thread

import redis
import greenswitch  

from configuration import (NODEID, ESL_HOST, ESL_PORT, ESL_SECRET, 
                           REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD, REDIS_TIMEOUT)
from utilities import logify, debugy, threaded


REDIS_CONNECTION_POOL = redis.BlockingConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD, 
                                                     decode_responses=True, max_connections=5, timeout=REDIS_TIMEOUT)
rdbconn = redis.StrictRedis(connection_pool=REDIS_CONNECTION_POOL)
pipe = rdbconn.pipeline()


def fssocket(reqdata):
    result = True
    try:
        commands = reqdata.get('commands')
        requestid = reqdata.get('requestid')
        fs = greenswitch.InboundESL(host=ESL_HOST, port=ESL_PORT, password=ESL_SECRET)
        fs.connect()
        for command in commands:
            response = fs.send(f'api {command}')
            if response:
                resultstr = response.data
                if '+OK' in resultstr[:3].upper(): 
                    _result = True
                else: 
                    _result = False
                    logify(f"module=liberator, space=bases, action=fssocket, requestid={requestid}, command={command}, result={resultstr}")
                result = bool(result and _result)
    except Exception as e:
        logify(f"module=liberator, space=bases, action=fssocket, reqdata={reqdata}, exception={e}, tracings={traceback.format_exc()}")
    finally:
        return result    


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
        callengine_acl_event = f'event:callengine:acl:{NODEID}'
        callengine_sipprofile_event = f'event:callengine:sipprofile:{NODEID}'
        callengine_gateway_event = f'event:callengine:gateway:{NODEID}'
        callengine_outcon_event = f'event:callengine:outbound:intcon:{NODEID}'
        callengine_incon_event = f'event:callengine:inbound:intcon:{NODEID}'
        callengine_startup_event = f'event:callengine:startup:{NODEID}'
        while not self.stop:
            events = None
            try:
                events = rdbconn.blpop([callengine_acl_event, 
                                        callengine_sipprofile_event,
                                        callengine_gateway_event,
                                        callengine_outcon_event,
                                        callengine_incon_event], REDIS_TIMEOUT)
                if events:
                    eventkey, eventvalue = events[0], json.loads(events[1])
                    logify(f"module=liberator, space=bases, action=catch_event, eventkey={eventkey}, eventvalue={eventvalue}")
                    prewait = eventvalue.get('prewait')
                    requestid = eventvalue.get('requestid')
                    # make the node run this task in different timestamp
                    time.sleep(int(prewait))

                    if eventkey==callengine_acl_event:
                        eventvalue.update({'commands': ['reloadacl', 'reloadxml']})
                        threaded(fssocket, eventvalue)
                        # reload firewall
                    elif eventkey==callengine_sipprofile_event:
                        pass
                    elif eventkey==callengine_gateway_event:
                        pass
                    elif eventkey==callengine_outcon_event:
                        pass
                    elif eventkey==callengine_incon_event:
                        pass
                    else:
                        pass
            except Exception as e:
                logify(f"module=liberator, space=bases, class=BaseEventHandler, action=run, events={events}, exception={e}, tracings={traceback.format_exc()}")
                time.sleep(5)
            finally:
                pass
