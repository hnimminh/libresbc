import time
import traceback
import random
import json
from threading import Thread
from subprocess import Popen, PIPE
import os

import redis
import greenswitch
from jinja2 import Environment, FileSystemLoader

from configuration import (NODEID, ESL_HOST, ESL_PORT, ESL_SECRET, 
                           REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD, REDIS_TIMEOUT)
from utilities import logify, debugy, threaded, listify, fieldjsonify, stringify, bdecode


REDIS_CONNECTION_POOL = redis.BlockingConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD, 
                                                     decode_responses=True, max_connections=5, timeout=REDIS_TIMEOUT)
rdbconn = redis.StrictRedis(connection_pool=REDIS_CONNECTION_POOL)

LIBRESBC_ENGINE_STARTUP = False

def fssocket(reqdata):
    result = True
    try:
        commands = reqdata.get('commands')
        requestid = reqdata.get('requestid')
        if commands:
            fs = greenswitch.InboundESL(host=ESL_HOST, port=ESL_PORT, password=ESL_SECRET)
            fs.connect()
            for command in commands:
                response = fs.send(f'api {command}')
                if response:
                    resultstr = response.data
                    if '+OK' in resultstr or 'Success' in resultstr or '+ok' in resultstr: 
                        _result = True
                    else: 
                        _result = False
                        logify(f"module=liberator, space=basemgr, action=fssocket, requestid={requestid}, command={command}, result={resultstr}")
                    result = bool(result and _result)
        logify(f"module=liberator, space=basemgr, action=fssocket, requestid={requestid}, commands={commands}, result={result}")
    except Exception as e:
        logify(f"module=liberator, space=basemgr, action=fssocket, reqdata={reqdata}, exception={e}, tracings={traceback.format_exc()}")
    finally:
        return result    


def osrename(old, new):
    try:
        if os.path.exists(old):
            os.rename(old, new)
    except: 
        return False
    return True


def osdelete(filename):
    try:
        if os.path.exists(filename): 
            os.remove(filename)
    except: 
        return False
    return True


_ENV = Environment(loader=FileSystemLoader('templates/nft'))
def nftupdate():
    result = True
    try:
        pipe = rdbconn.pipeline()
        # RTP PORTRANGE
        rtpportrange = list(map(fieldjsonify ,rdbconn.hmget('cluster:attributes', 'rtp_start_port', 'rtp_end_port')))
        # NETALIAS
        netaliasnames = rdbconn.smembers('nameset:netalias')
        for netaliasname in netaliasnames:
            pipe.hget(f'base:netalias:{netaliasname}', 'addresses')
        details = pipe.execute()
        netaliases = dict()
        for netaliasname, detail in zip(netaliasnames, details):
            addresses = [address for address in fieldjsonify(detail) if address.get('member') == NODEID][0]
            netaliases.update({netaliasname: addresses})
        # SIP PROFILES AND LISTEN ADDRESS/PORT
        profilenames = rdbconn.smembers('nameset:sipprofile')
        sipprofiles = dict()
        for profilename in profilenames:
            sip_port, sips_port, sip_address, rtp_address = rdbconn.hmget(f'sipprofile:{profilename}', 'sip_port', 'sips_port', 'sip_address', 'rtp_address')
            sip_ip = netaliases[sip_address]['listen']
            rtp_ip = netaliases[rtp_address]['listen']

            intconnameids = [item for item in rdbconn.smembers(f'engagement:sipprofile:{profilename}')]
            for intconnameid in intconnameids:
                pipe.hget(f'intcon:{intconnameid}', 'rtpaddrs')
            rtpaddrstrlist = pipe.execute()

            farendrtpaddrs = set([rtpaddr for rtpaddrstr in rtpaddrstrlist for rtpaddr in fieldjsonify(rtpaddrstr)])
            farendsipaddrs = rdbconn.smembers(f'farendsipaddrs:in:{profilename}')

            sipprofiles[profilename] = {'siptcpports': set([fieldjsonify(port) for port in [sip_port, sips_port] if port]), 
                                        'sipudpports': set([fieldjsonify(sip_port)]), 
                                        'sip_ip': sip_ip,
                                        'rtp_ip': rtp_ip,
                                        'farendrtpaddrs': stringify(farendrtpaddrs, ','),
                                        'farendsipaddrs': stringify(farendsipaddrs, ',')}

        template = _ENV.get_template("nftables.j2.conf")
        stream = template.render(sipprofiles=sipprofiles, rtpportrange=rtpportrange)
        nftfile = '/etc/nftables.conf.new'
        with open(nftfile, 'w') as nftf: nftf.write(stream)

        nftcmd = Popen(['/usr/sbin/nft', '-f', nftfile], stdout=PIPE, stderr=PIPE)    
        _, stderr = bdecode(nftcmd.communicate())
        if stderr:
            result = False
            stderr = stderr.replace('\n', '')
            logify(f"module=liberator, space=basemgr, action=nftupdate, nftfile={nftfile}, error={stderr}")
        else:
            old = osrename('/etc/nftables.conf', '/etc/nftables.conf.old')
            new = osrename('/etc/nftables.conf.new', '/etc/nftables.conf')
            if not (old and new):
                logify(f"module=liberator, space=basemgr, action=osrename, subtasks=rename:{old}:{new}")
            else:
                logify(f"module=liberator, space=basemgr, action=nftupdate, result=success")
    except Exception as e:
        result = False
        logify(f"module=liberator, space=basemgr, action=nftupdate, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

class BaseEventHandler(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.stop = False
        self.daemon = True
        self.setName('BaseEventHandler')

    def run(self):
        logify(f"module=liberator, space=basemgr, node={NODEID}, action=start_base_event_handler_thread")
        libreapi_netalias_event = f'event:libreapi:netalias:{NODEID}' # need reload sipprofile that use this netalias
        libreapi_acl_event = f'event:libreapi:acl:{NODEID}'
        libreapi_sipprofile_event = f'event:libreapi:sipprofile:{NODEID}'
        libreapi_gateway_event = f'event:libreapi:gateway:{NODEID}'
        libreapi_outcon_event = f'event:libreapi:outbound:intcon:{NODEID}'
        libreapi_incon_event = f'event:libreapi:inbound:intcon:{NODEID}'
        callengine_startup_event = f'event:callengine:startup:{NODEID}'
        while not self.stop:
            events = None
            try:
                events = rdbconn.blpop([libreapi_netalias_event,
                                        libreapi_acl_event, 
                                        libreapi_sipprofile_event,
                                        libreapi_gateway_event,
                                        libreapi_outcon_event,
                                        libreapi_incon_event,
                                        callengine_startup_event], REDIS_TIMEOUT)
                if events:
                    eventkey, eventvalue = events[0], json.loads(events[1])
                    logify(f"module=liberator, space=basemgr, action=catch_event, eventkey={eventkey}, eventvalue={eventvalue}")
                    prewait = eventvalue.get('prewait')
                    # make the node run this task in different timestamp
                    time.sleep(int(prewait))
                    # specify event
                    commands = list()
                    if eventkey == libreapi_netalias_event:
                        sipprofiles = eventvalue.get('sipprofiles')
                        for sipprofile in sipprofiles: 
                            commands.append(f'sofia profile {sipprofile} restart')
                        commands.append('reloadxml')
                    elif eventkey == libreapi_acl_event:
                        name = eventvalue.get('name')
                        _name = eventvalue.get('_name')
                        if name != _name: 
                            sipprofiles = eventvalue.get('sipprofiles')
                            for sipprofile in sipprofiles:
                                commands.append(f'sofia profile {sipprofile} rescan')
                        commands.append('reloadacl')
                    elif eventkey == libreapi_incon_event:
                        commands = ['reloadacl']
                    elif eventkey == libreapi_sipprofile_event:
                        action = eventvalue.get('action')
                        sipprofile = eventvalue.get('sipprofile')
                        _sipprofile = eventvalue.get('_sipprofile')
                        if action=='create':
                            commands = [f'sofia profile {sipprofile} start']
                        elif action=='delete':
                            commands = [f'sofia profile {_sipprofile} stop', 'reloadxml']
                        elif action=='update':
                            if sipprofile == _sipprofile: 
                                commands = [f'sofia profile {sipprofile} rescan', 'reloadxml']
                            else: 
                                commands = [f'sofia profile {_sipprofile} stop', f'sofia profile {sipprofile} start' , 'reloadxml']
                    elif eventkey == libreapi_gateway_event:
                        sipprofile = eventvalue.get('sipprofile')
                        _gateway = eventvalue.get('_gateway')
                        commands = [f'sofia profile {sipprofile} killgw {_gateway}', f'sofia profile {sipprofile} rescan', 'reloadxml']
                    elif eventkey == libreapi_outcon_event:
                        action = eventvalue.get('action')
                        sipprofile = eventvalue.get('sipprofile')
                        _sipprofile = eventvalue.get('_sipprofile')
                        gateways = eventvalue.get('gateways', [])
                        _gateways = eventvalue.get('_gateways', [])
                        if action=='create':
                            commands = [f'sofia profile {sipprofile} rescan']
                        elif action=='delete':
                            for _gateway, inuse in _gateways.items():
                                # the gateway that used by only this intcon, freely to remove
                                if inuse <= 1:
                                    commands.append(f'sofia profile {_sipprofile} killgw {_gateway}')
                        elif action=='update':
                            # change profile is executable only if only-profile-one use these gws or only one intcon use
                            if sipprofile != _sipprofile:
                                for _gateway in _gateways:
                                    commands.append(f'sofia profile {_sipprofile} killgw {_gateway}')
                            else:
                                for _gateway, inuse in _gateways.items():
                                    # remove gw if only-profile-one use these gws and not used by new intcon
                                    if inuse <= 1 and _gateway not in gateways:
                                        commands.append(f'sofia profile {_sipprofile} killgw {_gateway}')
                            # reload profile
                            commands.append(f'sofia profile {sipprofile} rescan')
                        # reload xml & distributor
                        commands += ['reloadxml', 'distributor_ctl reload']
                    elif eventkey == callengine_startup_event:
                        # pre-setup environment: voice/firewall/service
                        #commands = ['global_setvar LIBRESBC_FS_STARTUP=COMPLETED']
                        #eventvalue.update({'delay': commands})
                        pass
                    else:
                        pass
                    # execute esl commands
                    eventvalue.update({'commands': commands})
                    threaded(fssocket, eventvalue)
                    # firewall update
                    if eventkey in [libreapi_netalias_event, libreapi_acl_event, libreapi_incon_event, libreapi_outcon_event, libreapi_sipprofile_event, callengine_startup_event]:
                        threaded(nftupdate)
            except Exception as e:
                logify(f"module=liberator, space=basemgr, class=BaseEventHandler, action=run, events={events}, exception={e}, tracings={traceback.format_exc()}")
                time.sleep(5)
            finally:
                pass
