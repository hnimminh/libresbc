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
import json
from threading import Thread
from subprocess import Popen, PIPE, run as SubRun
import os
import redis
import redfs
from jinja2 import Environment, FileSystemLoader
from ipaddress import ip_address as IPvAddress, ip_network as IPvNetwork
from configuration import (CHANGE_CFG_CHANNEL, PERNODE_CHANNEL, SECURITY_CHANNEL, FIREWALL_NFTCMD_CHANNEL,
    REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD, REDIS_TIMEOUT,
    LIBRE_BUILTIN_FIREWALL, LIBRE_CONTAINERIZED, LIBRE_BUILTIN_REDIS, LIBRE_STANDALONE_MODEL,
)
from utilities import logger, threaded, fieldjsonify, stringify, bdecode


REDIS_CONNECTION_POOL = redis.BlockingConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD,
                                                     decode_responses=True, max_connections=5, timeout=REDIS_TIMEOUT)
rdbconn = redis.StrictRedis(connection_pool=REDIS_CONNECTION_POOL)

# global private variable; existing only with standalone setup
_NODEID = os.getenv('NODEID')

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
_NFT = Environment(loader=FileSystemLoader('nft'))
_DFTBANTIME = 900

@threaded
def nftupdate(data):
    if not LIBRE_BUILTIN_FIREWALL and not LIBRE_STANDALONE_MODEL:
        logger.info(f"module=liberator, space=basemgr, action=nftupdate, message=[skip action since buitin firewall is disabled]")
        return

    result = True
    try:
        requestid = data.get('requestid')
        pipe = rdbconn.pipeline()
        # FIREWARESET
        whiteset = rdbconn.smembers(f'firewall:whiteset')
        blackset = rdbconn.smembers(f'firewall:blackset')
        whitesetv6 = rdbconn.smembers(f'firewall:whitesetv6')
        blacksetv6 = rdbconn.smembers(f'firewall:blacksetv6')
        # RTP PORTRANGE
        rtpportrange = list(map(fieldjsonify ,rdbconn.hmget('cluster:attributes', 'rtp_start_port', 'rtp_end_port')))

        # PER NODE FIREWALL
        CLUSTERMEMBERS = set(rdbconn.smembers('cluster:members'))
        if _NODEID:
            # colocate libresbc and callengine
            CLUSTERMEMBERS = {_NODEID}

        for nodeid in CLUSTERMEMBERS:
            # NETALIAS
            netaliasnames = rdbconn.smembers('nameset:netalias')
            for netaliasname in netaliasnames:
                pipe.hget(f'base:netalias:{netaliasname}', 'addresses')
            details = pipe.execute()
            netaliases = dict()
            for netaliasname, detail in zip(netaliasnames, details):
                addresses = [address for address in fieldjsonify(detail) if address.get('member') == nodeid][0]
                netaliases.update({netaliasname: addresses})
            # SIP PROFILES AND LISTEN ADDRESS/PORT
            profilenames = rdbconn.smembers('nameset:sipprofile')
            sipprofiles = dict()
            for profilename in profilenames:
                sip_port, sips_port, sip_address, rtp_address = rdbconn.hmget(f'sipprofile:{profilename}', 'sip_port', 'sips_port', 'sip_address', 'rtp_address')
                sip_ip = netaliases[sip_address]['listen']
                rtp_ip = netaliases[rtp_address]['listen']
                sip_ip_version = IPvAddress(sip_ip).version
                rtp_ip_version = IPvAddress(rtp_ip).version

                intconnameids = [item for item in rdbconn.smembers(f'engagement:sipprofile:{profilename}')]

                # collect farend rtp ip addr per profile
                for intconnameid in intconnameids:
                    pipe.hget(f'intcon:{intconnameid}', 'rtpaddrs')
                rtpaddrstrlist = pipe.execute()
                farendrtpaddrs = set([rtpaddr for rtpaddrstr in rtpaddrstrlist for rtpaddr in fieldjsonify(rtpaddrstr)])
                _farendrtpaddrs = [ip for ip in farendrtpaddrs if IPvNetwork(ip).version==rtp_ip_version and not IPvNetwork(ip).is_loopback]

                # collect farend sip ip addr per profile
                # there is a SET of farend sip ip addr redis-key=[farendsipaddrs:in:{profilename}]
                # but it only for INBOUND then do same as farend rtp ip addr
                # sipaddrs field for outbound is supported later (then need to handle null)
                for intconnameid in intconnameids:
                    pipe.hget(f'intcon:{intconnameid}', 'sipaddrs')
                sipaddrstrlist = pipe.execute()
                farendsipaddrs = set([sipaddr for sipaddrstr in sipaddrstrlist if sipaddrstr for sipaddr in fieldjsonify(sipaddrstr)])
                _farendsipaddrs = [ip for ip in farendsipaddrs if IPvNetwork(ip).version==sip_ip_version and not IPvNetwork(ip).is_loopback]

                sipprofiles[profilename] = {
                    'siptcpports': set([fieldjsonify(port) for port in [sip_port, sips_port] if port]),
                    'sipudpports': fieldjsonify(sip_port),
                    'sip_ip': sip_ip,
                    'rtp_ip': rtp_ip,
                    f'farendrtpaddrv{rtp_ip_version}s': _farendrtpaddrs,
                    f'farendsipaddrv{sip_ip_version}s': _farendsipaddrs
                }
            logger.debug(f"module=liberator, space=basemgr, action=nftupdate, nodeid={nodeid}, sipprofiles={sipprofiles}")

            # RULE FILE
            template = _NFT.get_template("nftables.j2.conf")
            stream = template.render(whiteset=whiteset, blackset=blackset, whitesetv6=whitesetv6, blacksetv6=blacksetv6,
                                    rtpportrange=rtpportrange, sipprofiles=sipprofiles, dftbantime=_DFTBANTIME)

            # fire pubsub event for firewall
            logger.info(f"module=liberator, space=basemgr, requestid={requestid}, action=nftupdate-publish")
            rdbconn.publish(FIREWALL_NFTCMD_CHANNEL, json.dumps({'type': 'stream', 'data': stream}))
    except Exception as e:
        result = False
        logger.critical(f"module=liberator, space=basemgr, action=nftupdate, data={data}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result

#---------------------------------------------------------------------------------
_nftdelimiter_ = ', '
@threaded
def nftsets(setname, ops, srcips, bantime=None):
    if not LIBRE_BUILTIN_FIREWALL and not LIBRE_STANDALONE_MODEL:
        logger.info(f"module=liberator, space=basemgr, action=nftsets, message=[skip action since buitin firewall is disabled]")
        return

    result = True
    try:
        if bantime:
            if bantime == _DFTBANTIME: element = f'{{ {stringify(srcips, _nftdelimiter_)} }}'
            else:
                _es = [f'{srcip} timeout {bantime}s' for srcip in srcips]
                element = f'{{ {stringify(_es, _nftdelimiter_)} }}'
        else:
            element = f'{{ {stringify(srcips, _nftdelimiter_)} }}'

        # fire pubsub event for firewall
        logger.info(f"module=liberator, space=basemgr, action=nftsets-publish, ops={ops}, setname={setname}, srcips={srcips}, element={element}")
        rdbconn.publish(FIREWALL_NFTCMD_CHANNEL, json.dumps({'type': 'cmd', 'data': f'nft {ops} element inet LIBREFW {setname} {element}'}))
    except Exception as e:
        result = False
        logger.critical(f"module=liberator, space=basemgr, action=nftsets, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# B2BUA CONTROL
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
_FSXML = Environment(loader=FileSystemLoader('fscfg'))
@threaded
def fsinstance(data):
    if not LIBRE_STANDALONE_MODEL:
        logger.info(f"module=liberator, space=basemgr, action=fsinstance, message=[skip this action with standardalone model]")
        return

    result = True
    xmlfile = '/usr/local/etc/freeswitch/freeswitch.xml'
    clifile = '/etc/fs_cli.conf'
    try:
        xmltemplate = _FSXML.get_template("xml/freeswitch.xml")
        xmlstream = xmltemplate.render()
        with open(xmlfile, 'w') as fsf: fsf.write(xmlstream)

        clitemplate = _FSXML.get_template("etc/fs_cli.conf")
        clistream = clitemplate.render()
        with open(clifile, 'w') as clif: clif.write(clistream)

        if LIBRE_CONTAINERIZED:
            SubRun(['/usr/local/bin/freeswitch', '-reincarnate'])
            return

        fsrun = Popen(['/usr/local/bin/freeswitch', '-nc', '-reincarnate'], stdout=PIPE, stderr=PIPE)
        _, stderr = bdecode(fsrun.communicate())

        if stderr and not stderr.endswith('Backgrounding.'):
            result = False
            stderr = stderr.replace('\n', '')
            logger.error(f"module=liberator, space=basemgr, action=fsinstance.fsrun, error={stderr}")
        else: logger.info(f"module=liberator, space=basemgr, action=fsinstance.fsrun, result=success")
    except Exception as e:
        result = False
        logger.critical(f"module=liberator, space=basemgr, action=fsinstance, data={data}, exception={e}, traceback={traceback.format_exc()}")
    finally:
        return result


@threaded
def fssocket(requestid, commands, delay, sockets):
    result, fs = False, None
    try:
        # connecting
        logger.info(f"module=liberator, space=basemgr, func=fssocket, action=preparing, requestid={requestid}, nodeids={[socket.get('nodeid') for socket in sockets]}, commands={commands}, delay={delay}")
        for socket in sockets:
            ipaddr = socket.get('ipaddr')
            port = socket.get('port')
            password = socket.get('password')
            nodeid = socket.get('nodeid')
            fs = redfs.InboundESL(host=ipaddr, port=port, password=password, timeout=10)
            for _ in range(0,3):
                try:
                    fs.connect()
                    if fs.connected: break
                except:
                    if delay:
                        time.sleep(delay)
                    else:
                        time.sleep(5)
            # send api commands
            if commands and fs.connected:
                result = True
                for command in commands:
                    response = fs.send(f'api {command}')
                    if response:
                        resultstr = response.data
                        if '+OK' in resultstr or 'Success' in resultstr or '+ok' in resultstr:
                            _result = True
                        else:
                            _result = False
                            logger.warning(f"module=liberator, space=basemgr, func=fssocket, requestid={requestid}, nodeid={nodeid},command={command}, result={resultstr}")
                        result = bool(result and _result)
            logger.info(f"module=liberator, space=basemgr, func=fssocket, connected={fs.connected}, requestid={requestid}, nodeid={nodeid}, commands={commands}, result={result}")
    except Exception as e:
        logger.error(f"module=liberator, space=basemgr, func=fssocket, commands={commands}, requestid={requestid}, esno={len(sockets)} exception={e}, tracings={traceback.format_exc()}")
    finally:
        if fs and fs.connected: fs.stop()
        return result


#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# RDB UNIX SOCKET INSTANCE
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
@threaded
def rdbinstance():
    if not LIBRE_BUILTIN_REDIS or not LIBRE_STANDALONE_MODEL:
        logger.info(f"module=liberator, space=basemgr, action=rdbinstance, message=[skip action since buitin redis is disabled]")
        return

    try:
        logger.info(f"module=liberator, space=basemgr, action=rdbinstance, state=initiating")
        rdbrun = Popen(['/usr/bin/redis-server', '--bind', '127.0.0.1', '--port', '6379', '--pidfile', '/run/redis/redis.pid', '--unixsocket',
                        '/run/redis/redis.sock', '--unixsocketperm', '755', '--dbfilename', 'libresbc.rdb', '--dir', '/run/redis', '--loglevel', 'warning'])
        _, stderr = bdecode(rdbrun.communicate())
        if stderr:
            logger.error(f"module=liberator, space=basemgr, action=rdbinstance.rdbrun, error={stderr}")
        else:
            logger.info(f"module=liberator, space=basemgr, action=rdbinstance.rdbrun, result=success")
    except Exception as e:
        logger.critical(f'module=liberator, space=basemgr, action=exception, exception={e}, tracings={traceback.format_exc()}')


#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# BASE RESOURCE STARTUP
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
_NGLUA = Environment(loader=FileSystemLoader('nglua'))
@threaded
def basestartup():
    result = False
    try:
        logger.info(f"module=liberator, space=basemgr, action=basestartup, state=initiating")
        data = {'portion': 'liberator:startup', 'requestid': '00000000-0000-0000-0000-000000000000'}
        rdbinstance()
        fsinstance(data)
        nftupdate(data)
        result = True
    except redis.RedisError as e:
        time.sleep(10)
    except Exception as e:
        logger.critical(f'module=liberator, space=basemgr, action=exception, exception={e}, tracings={traceback.format_exc()}')
        time.sleep(5)
    finally:
        logger.info(f"module=liberator, space=basemgr, action=basestartup, state={'completed' if result else 'dropped'}")


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
        logger.info(f"module=liberator, space=basemgr, thread={self.getName()}, action=start")
        # portions
        _CLUSTER_   = 'cluster'
        _NETALIAS_  = 'netalias'
        _ACL_       = 'acl'
        _INCNX_     = 'inbound:intcon'
        _OUTCNX_    = 'outbound:intcon'
        _SOFIASIP_  = 'sofiasip'
        _SOFIAGW_   = 'sofiagw'
        _POLICY_    = 'policy:domain'
        _CFGAPISIP_ = 'cfgapi:sip'
        # listen events
        while True:
            try:
                pubsub = rdbconn.pubsub()
                pubsub.subscribe([CHANGE_CFG_CHANNEL, PERNODE_CHANNEL])
                for message in pubsub.listen():
                    logger.info(f'module=liberator, space=basemgr, action=report, message={message}')
                    msgtype = message.get("type")
                    if msgtype == "message":
                        data = json.loads(message.get("data"))
                        portion = data.get('portion')
                        requestid = data.get('requestid')
                        delay = data.get('delay')
                        nodeid = None
                        # specify event
                        commands = list()
                        if portion == _NETALIAS_:
                            sipprofiles = data.get('sipprofiles')
                            for sipprofile in sipprofiles:
                                commands.append(f'sofia profile {sipprofile} restart')
                            commands.append('reloadxml')
                        elif portion == _ACL_:
                            name = data.get('name')
                            _name = data.get('_name')
                            if name != _name:
                                sipprofiles = data.get('sipprofiles')
                                for sipprofile in sipprofiles:
                                    commands.append(f'sofia profile {sipprofile} rescan')
                            commands.append('reloadacl')
                        elif portion == _INCNX_:
                            commands = ['reloadacl']
                        elif portion == _SOFIASIP_:
                            action = data.get('action')
                            sipprofile = data.get('sipprofile')
                            _sipprofile = data.get('_sipprofile')
                            if action=='create':
                                commands = [f'sofia profile {sipprofile} start']
                            elif action=='delete':
                                commands = [f'sofia profile {_sipprofile} stop', 'reloadxml']
                            elif action=='update':
                                if sipprofile == _sipprofile:
                                    commands = [f'sofia profile {sipprofile} restart', 'reloadxml']
                                else:
                                    commands = [f'sofia profile {_sipprofile} stop', f'sofia profile {sipprofile} start' , 'reloadxml']
                        elif portion == _SOFIAGW_:
                            sipprofile = data.get('sipprofile')
                            _gateway = data.get('_gateway')
                            commands = [f'sofia profile {sipprofile} killgw {_gateway}', f'sofia profile {sipprofile} rescan', 'reloadxml']
                        elif portion == _OUTCNX_:
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
                        elif portion == _POLICY_:
                            layer = data.get('layer')
                            kaminstance({'layer': layer, '_layer': layer, 'requestid': requestid})
                        elif portion == _CLUSTER_:
                            fsgvars = data.get('fsgvars')
                            commands = [f'global_setvar {fsgvar}' for fsgvar in fsgvars]
                        elif portion == _CFGAPISIP_:
                            nodeid = data.get('nodeid')
                            fsgvars = data.get('fsgvars')
                            commands = [f'global_setvar {fsgvar}' for fsgvar in fsgvars]
                        else:
                            pass
                        # execute esl commands
                        if commands:
                            if nodeid:
                                _socket = rdbconn.hget('DISCOVERY', nodeid)
                                sockets = [json.loads(_socket)]
                            else:
                                _socketall = rdbconn.hgetall('DISCOVERY')
                                sockets = [json.loads(_socket) for _,_socket in _socketall.items()]
                            fssocket(requestid, commands, delay, sockets)
                        # firewall update
                        if portion in [_NETALIAS_, _ACL_, _INCNX_, _OUTCNX_, _SOFIASIP_]:
                            nftupdate(data)
            except redis.RedisError as e:
                time.sleep(5)
            except Exception as e:
                logger.error(f'module=liberator, space=basemgr, action=exception, exception={e}, tracings={traceback.format_exc()}')
                time.sleep(2)
            finally:
                if pubsub in locals():
                    pubsub.close()

#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
# SECURIRY HANDLE
#-----------------------------------------------------------------------------------------------------------------------------------------------------------------------
class SecurityEventHandler(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.stop = False
        self.daemon = True
        self.setName('SecurityEventHandler')

    def run(self):
        logger.info(f"module=liberator, space=basemgr, thread={self.getName()}, action=start")
        # portions
        _kamiauthfailure = 'kami:authfailure'
        _kamiattackavoid = 'kami:attackavoid'
        _kamiantiflooding = 'kami:antiflooding'
        _apiwhiteset = 'api:whiteset'
        _apiblackset = 'api:blackset'
        _apiwhitesetv6 = 'api:whitesetv6'
        _apiblacksetv6 = 'api:blacksetv6'
        while True:
            try:
                pubsub = rdbconn.pubsub()
                pubsub.subscribe([SECURITY_CHANNEL])
                for message in pubsub.listen():
                    msgtype = message.get("type")
                    if msgtype == "message":
                        data = json.loads(message.get("data"))
                        portion = data.get('portion')
                        srcips = data.get('srcips')
                        ops = 'delete' if data.get('_flag') else 'add'
                        if srcips and portion in [_kamiauthfailure, _kamiattackavoid, _kamiantiflooding]:
                            # there is only 1 srcip in these portions
                            bantime = data.get('bantime')
                            ipversion = IPvAddress(srcips[0]).version
                            if ipversion == 4:
                                nftsets('TemporaryBlocks', ops, srcips, bantime)
                            if ipversion == 6:
                                nftsets('TemporaryBlocksV6', ops, srcips, bantime)
                        if srcips and portion==_apiwhiteset:
                            nftsets('WhiteHole', ops, srcips)
                        if srcips and portion==_apiblackset:
                            nftsets('BlackHole', ops, srcips)
                        if srcips and portion==_apiwhitesetv6:
                            nftsets('WhiteHoleV6', ops, srcips)
                        if srcips and portion==_apiblacksetv6:
                            nftsets('BlackHoleV6', ops, srcips)
            except redis.RedisError as e:
                time.sleep(5)
            except Exception as e:
                logger.error(f'module=liberator, space=basemgr, action=exception, exception={e}, tracings={traceback.format_exc()}')
                time.sleep(2)
            finally:
                if pubsub in locals():
                    pubsub.close()
