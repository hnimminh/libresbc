#
# liberator:basemgr.py
#
# The Initial Developer of the Original Code is
# Minh Minh <hnimminh at[@] outlook dot[.] com>
# Portions created by the Initial Developer are Copyright (C) the Initial Developer.
# All Rights Reserved.
#

import time
import traceback
import random
import json
from threading import Thread
from subprocess import Popen, PIPE
import os

import redis
import redfs
from jinja2 import Environment, FileSystemLoader

from configuration import (NODEID, CHANGE_CFG_CHANNEL, ESL_HOST, ESL_PORT, ESL_SECRET,
                           REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD, REDIS_TIMEOUT)
from utilities import logify, debugy, threaded, listify, fieldjsonify, stringify, bdecode


REDIS_CONNECTION_POOL = redis.BlockingConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD,
                                                     decode_responses=True, max_connections=5, timeout=REDIS_TIMEOUT)
rdbconn = redis.StrictRedis(connection_pool=REDIS_CONNECTION_POOL)

LIBRESBC_ENGINE_STARTUP = False


#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# B2BUA CONTROL
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
@threaded
def fssocket(reqdata):
    result, fs = True, None
    try:
        commands = reqdata.get('commands')
        requestid = reqdata.get('requestid')
        defer = reqdata.get('defer')
        if defer: time.sleep(defer)
        # connecting
        fs = redfs.InboundESL(host=ESL_HOST, port=ESL_PORT, password=ESL_SECRET, timeout=10)
        for _ in range(0,3):
            try:
                fs.connect()
                if fs.connected: break
            except: time.sleep(5)
        # send api commands
        if commands and fs.connected:
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
        logify(f"module=liberator, space=basemgr, action=fssocket, connected={fs.connected}, requestid={requestid}, commands={commands}, result={result}")
    except Exception as e:
        logify(f"module=liberator, space=basemgr, action=fssocket, reqdata={reqdata}, exception={e}, tracings={traceback.format_exc()}")
    finally:
        if fs and fs.connected: fs.stop()
        return result


#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# OS
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
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


#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# NETFILTER TABLE
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
_ENV = Environment(loader=FileSystemLoader('templates/nft'))

@threaded
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


#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# PROXY MANAGE
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------


#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# BASES MANAGE HANDLE
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
class BaseEventHandler(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.stop = False
        self.daemon = True
        self.setName('BaseEventHandler')

    def run(self):
        logify(f"module=liberator, space=basemgr, node={NODEID}, action=start")
        # portions
        _netalias       = 'netalias'
        _acl            = 'acl'
        _inboundcnx     = 'inbound:intcon'
        _outboundcnx    = 'inbound:intcon'
        _sipprofile     = 'sipprofile'
        _gateway        = 'gateways'
        _ngstartup      = 'ngstartup'
        # listen events
        while True:
            try:
                pubsub = rdbconn.pubsub()
                pubsub.subscribe([CHANGE_CFG_CHANNEL, f'NG:STARTUP:{NODEID}'])
                for message in pubsub.listen():
                    logify(f'module=liberator, space=basemgr, action=report, message={message}')
                    msgtype = message.get("type")
                    if msgtype == "message":
                        data = json.loads(message.get("data"))
                        portion = data.get('portion')
                        # specify event
                        commands = list()
                        if portion == _netalias:
                            sipprofiles = data.get('sipprofiles')
                            for sipprofile in sipprofiles:
                                commands.append(f'sofia profile {sipprofile} restart')
                            commands.append('reloadxml')
                        elif portion == _acl:
                            name = data.get('name')
                            _name = data.get('_name')
                            if name != _name:
                                sipprofiles = data.get('sipprofiles')
                                for sipprofile in sipprofiles:
                                    commands.append(f'sofia profile {sipprofile} rescan')
                            commands.append('reloadacl')
                        elif portion == _inboundcnx:
                            commands = ['reloadacl']
                        elif portion == _sipprofile:
                            action = data.get('action')
                            sipprofile = data.get('sipprofile')
                            _sipprofile = data.get('_sipprofile')
                            if action=='create':
                                commands = [f'sofia profile {sipprofile} start']
                            elif action=='delete':
                                commands = [f'sofia profile {_sipprofile} stop', 'reloadxml']
                            elif action=='update':
                                if sipprofile == _sipprofile:
                                    commands = [f'sofia profile {sipprofile} rescan', 'reloadxml']
                                else:
                                    commands = [f'sofia profile {_sipprofile} stop', f'sofia profile {sipprofile} start' , 'reloadxml']
                        elif portion == _gateway:
                            sipprofile = data.get('sipprofile')
                            _gateway = data.get('_gateway')
                            commands = [f'sofia profile {sipprofile} killgw {_gateway}', f'sofia profile {sipprofile} rescan', 'reloadxml']
                        elif portion == _outboundcnx:
                            action = data.get('action')
                            sipprofile = data.get('sipprofile')
                            _sipprofile = data.get('_sipprofile')
                            gateways = data.get('gateways', [])
                            _gateways = data.get('_gateways', [])
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
                        elif portion == _ngstartup:
                            # pre-setup environment: voice/firewall/service
                            #commands = ['global_setvar LIBRESBC_FS_STARTUP=COMPLETED']
                            #eventvalue.update({'delay': commands})
                            pass
                        else:
                            pass
                        # execute esl commands
                        data.update({'commands': commands})
                        fssocket(data)
                        # firewall update
                        if portion in [_netalias, _acl, _inboundcnx, _outboundcnx, _sipprofile, _ngstartup]:
                            nftupdate()
            except redis.RedisError as e:
                time.sleep(5)
            except Exception as e:
                logify(f'module=liberator, space=basemgr, action=exception, exception={e}, tracings={traceback.format_exc()}')
                time.sleep(2)
            finally:
                pubsub.close()
