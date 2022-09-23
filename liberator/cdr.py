#
# liberator:cdr.py
#
# The Initial Developer of the Original Code is
# Minh Minh <hnimminh at[@] outlook dot[.] com>
# Portions created by the Initial Developer are Copyright (C) the Initial Developer.
# All Rights Reserved.
#

import time
import traceback
from threading import Thread
from math import exp
from random import randint, choice, shuffle
from datetime import datetime, date, timezone
import json

import requests
import redis

from configuration import (_APPLICATION, _SWVERSION, NODEID, SWCODECS, CLUSTERS,
                           REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD, SCAN_COUNT, REDIS_TIMEOUT,
                           LOGDIR, HTTPCDR_ENDPOINTS, DISKCDR_ENABLE)
from utilities import logify, debugy

REDIS_CONNECTION_POOL = redis.BlockingConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD,
                                                     decode_responses=True, max_connections=10, timeout=REDIS_TIMEOUT)
rdbconn = redis.StrictRedis(connection_pool=REDIS_CONNECTION_POOL)


SIP_RESPONSES = {
    100: "TRYING",
    180: 'RINGING',
    181: 'CALL IS BEING FORWARDED',
    182: 'QUEUED',
    183: 'SESSION PROGRESS',
    199: 'EARLY DIALOG TERMINATED',
    200: 'OK',
    202: 'ACCEPTED',
    204: 'NO NOTIFICATION',
    300: 'MULTIPLE CHOICES',
    301: 'MOVED PERMANENTLY',
    302: 'MOVED TEMPORARILY',
    305: 'USE PROXY',
    380: 'ALTERNATIVE SERVICE',
    400: 'BAD REQUEST',
    401: 'UNAUTHORIZED',
    402: 'PAYMENT REQUIRED',
    403: 'FORBIDDEN',
    404: 'NOT FOUND',
    405: 'METHOD NOT ALLOWED',
    406: 'NOT ACCEPTABLE',
    407: 'PROXY AUTHENTICATION REQUIRED',
    408: 'REQUEST TIMEOUT',
    409: 'CONFLICT',
    410: 'GONE',
    411: 'LENGTH REQUIRED',
    412: 'CONDITIONAL REQUEST FAILED',
    413: 'REQUEST ENTITY TOO LARGE',
    414: 'REQUEST-URI TOO LONG',
    415: 'UNSUPPORTED MEDIA TYPE',
    416: 'UNSUPPORTED URI SCHEME',
    417: 'UNKNOWN RESOURCE-PRIORITY',
    420: 'BAD EXTENSION',
    421: 'EXTENSION REQUIRED',
    422: 'SESSION INTERVAL TOO SMALL',
    423: 'INTERVAL TOO BRIEF',
    424: 'BAD LOCATION INFORMATION',
    425: 'BAD ALERT MESSAGE',
    428: 'USE IDENTITY HEADER',
    429: 'PROVIDE REFERRER IDENTITY',
    430: 'FLOW FAILED',
    433: 'ANONYMITY DISALLOWED',
    436: 'BAD IDENTITY-INFO',
    437: 'UNSUPPORTED CERTIFICATE',
    438: 'INVALID IDENTITY HEADER',
    439: 'FIRST HOP LACKS OUTBOUND SUPPORT',
    440: 'MAX-BREADTH EXCEEDED',
    469: 'BAD INFO PACKAGE',
    470: 'CONSENT NEEDED',
    480: 'TEMPORARILY UNAVAILABLE',
    481: 'CALL/TRANSACTION DOES NOT EXIST',
    482: 'LOOP DETECTED',
    483: 'TOO MANY HOPS',
    484: 'ADDRESS INCOMPLETE',
    485: 'AMBIGUOUS',
    486: 'BUSY HERE',
    487: 'REQUEST TERMINATED',
    488: 'NOT ACCEPTABLE HERE',
    489: 'BAD EVENT',
    491: 'REQUEST PENDING',
    493: 'UNDECIPHERABLE',
    494: 'SECURITY AGREEMENT REQUIRED',
    500: 'INTERNAL SERVER ERROR',
    501: 'NOT IMPLEMENTED',
    502: 'BAD GATEWAY',
    503: 'SERVICE UNAVAILABLE',
    504: 'SERVER TIME-OUT',
    505: 'VERSION NOT SUPPORTED',
    513: 'MESSAGE TOO LARGE',
    555: 'PUSH NOTIFICATION SERVICE NOT SUPPORTED',
    580: 'PRECONDITION FAILURE',
    600: 'BUSY EVERYWHERE',
    603: 'DECLINE',
    604: 'DOES NOT EXIST ANYWHERE',
    606: 'NOT ACCEPTABLE',
    607: 'UNWANTED',
    608: 'REJECTED'
}

SIP_DISPOSITIONS = {
    100: "TRYING",
    180: 'RINGING',
    181: 'FORWARDING',
    182: 'QUEUED',
    183: 'PROGRESS',
    199: 'TERMINATION',
    200: 'ANSWERED',
    202: 'ANSWERED',
    204: 'ANSWERED',
    301: 'REDIRECTION',
    302: 'REDIRECTION',
    305: 'REDIRECTION',
    380: 'REDIRECTION',
    400: 'CONGESTION',
    401: 'CONGESTION' ,
    402: 'CONGESTION',
    403: 'CONGESTION',
    404: 'CONGESTION',
    405: 'CONGESTION',
    406: 'CONGESTION',
    407: 'CONGESTION',
    408: 'NOANSWER',
    409: 'CONGESTION',
    410: 'CONGESTION',
    411: 'CONGESTION',
    413: 'CONGESTION',
    414: 'CONGESTION',
    415: 'CONGESTION',
    420: 'CONGESTION',
    480: 'NOANSWER',
    481: 'CONGESTION',
    482: 'CONGESTION',
    483: 'CONGESTION',
    484: 'CONGESTION',
    485: 'CONGESTION',
    486: 'BUSY',
    487: 'CANCEL',
    488: 'CONGESTION',
    500: 'CONGESTION',
    501: 'CONGESTION',
    502: 'CONGESTION',
    503: 'CONGESTION',
    504: 'CONGESTION',
    505: 'CONGESTION',
    580: 'CONGESTION',
    600: 'BUSY',
    603: 'CONGESTION',
    604: 'CONGESTION',
    606: 'CONGESTION'
}


def fmtime(epochtime):
    try:
        epochtime = float(epochtime)
        if epochtime == 0: None
        else: return datetime.fromtimestamp(epochtime, tz=timezone.utc).isoformat()
    except:
        return None


def reebackoff(f, n):
    # random euler exponential backoff timer
    if n == 0: return randint(1, f)
    else: return randint(round(f * exp(1) ** (n-1)), round(f * exp(1) ** n))


def parseruri(ruri):
    # sip:84987654321@libre.io:5060;transport=udp
    host, port, transport = None, None, None
    try:
        netparts = ruri.split('@')
        transport = netparts[1].split(';transport=')[1].split(';')[0]
        host, port = netparts[1].split(';transport=')[0].split(':')
    finally:
        return host, port, transport

class CDRHandler(Thread):
    def __init__(self, uuid, details):
        self.stop = False
        self.uuid = uuid
        self.details = details
        Thread.__init__(self)

    def run(self):
        MAXRETRY = 5
        try:
            # parse and refine cdr
            self.refine()
            logify(f"module=liberator, space=cdr, action=cdrnotifier, uuid={self.uuid}, data={self.cdrdata}")
            # save the cdr to destination
            cdrsaved = True; waiting = 5; attempt = 0
            while attempt < MAXRETRY and not self.stop:
                # primary task to save cdr
                if HTTPCDR_ENDPOINTS:
                    cdrsaved = self.httpsave()

                # data stored guarantee process
                attempt += 1
                if cdrsaved:
                    if attempt > MAXRETRY-2:
                        logify(f"module=liberator, space=cdr, action=savehandler, state=clear, nodeid={NODEID}, uuid={self.uuid}, attempted={attempt}")
                    break
                else:
                    backoff = reebackoff(waiting, attempt)
                    if attempt >= MAXRETRY-2:
                        logify(f"module=liberator, space=cdr, action=savehandler, state=stuck, nodeid={NODEID}, uuid={self.uuid}, attempted={attempt}, backoff={backoff}")
                    time.sleep(backoff)

            # save cdr to local file
            if (not cdrsaved) or DISKCDR_ENABLE:
                self.filesave()

            # post process after saving the cdr, clean cdr on redis
            rcleaned = False; waiting = 5; attempt = 0
            while attempt < MAXRETRY and not self.stop:
                rcleaned = self.rclean()
                attempt += 1
                if rcleaned:
                    if attempt > MAXRETRY-2:
                        logify(f"module=liberator, space=cdr, action=rdbhandler, state=clear, nodeid={NODEID}, uuid={self.uuid}, attempted={attempt}")
                    break
                else:
                    backoff = reebackoff(waiting, attempt)
                    if attempt >= MAXRETRY-2:
                        logify(f"module=liberator, space=cdr, action=rdbhandler, state=stuck, nodeid={NODEID}, uuid={self.uuid}, attempted={attempt}, backoff={backoff}")
                    time.sleep(backoff)

        except Exception as e:
            logify(f"module=liberator, space=cdr, class=CDRHandler, action=run, uuid={self.uuid}, exception={e}, tracings={traceback.format_exc()}")
            time.sleep(5)
        finally: pass

    def refine(self):
        try:
            uuid = self.details.get('uuid')
            seshid = self.details.get('seshid')
            direction = self.details.get('direction')
            sipprofile = self.details.get('sipprofile')
            context = self.details.get('context')
            nodeid = self.details.get('nodeid')
            intconname = self.details.get('intconname')
            gateway = self.details.get('gateway_name')
            user_agent = self.details.get('user_agent')
            callid = self.details.get('callid')
            caller_name = self.details.get('caller_name')
            caller_number = self.details.get('caller_number')
            destination_number = self.details.get('destination_number')
            # datatime
            start_time = fmtime(self.details.get('start_time'))
            answer_time  = fmtime(self.details.get('answer_time'))
            end_time = fmtime(self.details.get('end_time'))
            duration = self.details.get('duration', 0)
            # sip address
            sip_network_ip = self.details.get('sip_network_ip')
            sip_network_port = self.details.get('sip_network_port')
            sip_local_network_addr = self.details.get('sip_local_network_addr')
            sip_req_uri = self.details.get('sip_req_uri')
            # access
            access_authid = self.details.get('access_authid')
            access_srcip = self.details.get('access_srcip')
            access_userid = self.details.get('access_userid')
            # transport
            transport = 'udp'
            if direction.lower() == 'inbound':
                sip_via_protocol = self.details.get('sip_via_protocol')
                if sip_via_protocol: transport = sip_via_protocol
            else:
                ruri_host, ruri_port, ruri_transport = parseruri(sip_req_uri)
                if ruri_transport: transport = ruri_transport
            # media
            remote_media_ip = self.details.get('remote_media_ip')
            remote_media_port = self.details.get('remote_media_port')
            local_media_ip = self.details.get('local_media_ip')
            local_media_port = self.details.get('local_media_port')
            advertised_media_ip = self.details.get('advertised_media_ip', '')
            read_codec = self.details.get('read_codec')
            write_codec = self.details.get('write_codec')
            rtp_crypto = self.details.get('rtp_has_crypto')
            # HANGUP CAUSE: 'NORMAL_CLEARING', 'ORIGINATOR_CANCEL' ...
            hangup_cause = self.details.get('hangup_cause')
            libre_hangup_cause = self.details.get('libre_hangup_cause')
            if libre_hangup_cause:
                hangup_cause = f'{hangup_cause}_BY_{libre_hangup_cause}'
            # HANGUP DEPOSITION: RECV_BYE, SEND_BYE ...
            hangup_disposition = self.details.get('hangup_disposition')
            disposition = f'LIBRESBC_{hangup_disposition.upper()}' if hangup_disposition else 'UNDEFINED'
            # STATUS: ANSWER, BUSY DERIVED FROM SIP RESPONSES: 400, 503..
            sip_hangup_cause = self.details.get('sip_hangup_cause')
            bridge_sip_hangup_cause = self.details.get('bridge_sip_hangup_cause')
            libre_sip_hangup_cause = self.details.get('libre_sip_hangup_cause')
            sip_redirected_to = self.details.get('sip_redirected_to')
            if sip_hangup_cause: sip_resp_code = sip_hangup_cause
            elif bridge_sip_hangup_cause: sip_resp_code = bridge_sip_hangup_cause
            elif libre_sip_hangup_cause: sip_resp_code = libre_sip_hangup_cause
            else:
                if duration and duration.isdigit() and int(duration) > 0: sip_resp_code = 'sip:200'
                elif sip_redirected_to: sip_resp_code = 'sip:302'
                else: sip_resp_code = 'sip:000'
            status = SIP_DISPOSITIONS.get(int(sip_resp_code.split(':')[1]), 'FAILURE')

            cdrdata = {
                'uuid': uuid,
                'seshid': seshid,
                'direction': direction,
                'sipprofile': sipprofile,
                'context': context,
                'nodeid': nodeid,
                'intconname': intconname,
                'gateway': gateway,
                'user_agent': user_agent,
                'callid': callid,
                'caller_name': caller_name,
                'caller_number': caller_number,
                'destination_number': destination_number,
                'start_time': start_time,
                'answer_time': answer_time,
                'end_time': end_time,
                'duration': duration,
                'sip_network_ip': sip_network_ip,
                'sip_network_port': sip_network_port,
                'sip_local_network_addr': sip_local_network_addr,
                'transport': transport,
                'remote_media_ip': remote_media_ip,
                'remote_media_port': remote_media_port,
                'local_media_ip': local_media_ip,
                'local_media_port': local_media_port,
                'read_codec': read_codec,
                'write_codec': write_codec,
                'rtp_crypto': rtp_crypto,
                'hangup_cause': hangup_cause,
                'sip_resp_code' : sip_resp_code,
                'disposition': disposition,
                'status': status,
            }
            if access_authid: cdrdata['access_authid'] = access_authid
            if access_srcip: cdrdata['access_srcip'] = access_srcip
            if access_userid: cdrdata['access_userid'] = access_userid
        except Exception as e:
            logify(f"module=liberator, space=cdr, class=CDRHandler, action=refine, uuid={self.uuid}, exception={e}, tracings={traceback.format_exc()}")
            cdrdata = {}
        finally:
           self.cdrdata = cdrdata

    def filesave(self):
        try:
            filename = f'{date.today().strftime("%Y-%m-%d")}.cdr.nice.json'
            cdrjson = json.dumps(self.details)
            logify(f"module=liberator, space=cdr, action=filesave, nodeid={NODEID}, data={cdrjson}, filename={filename}")
            with open(f'{LOGDIR}/cdr/{filename}', "a") as jsonfile:
                jsonfile.write(cdrjson + '\n')
        except Exception as e:
            logify(f"module=liberator, space=cdr, class=CDRHandler, action=filesave, exception={e}, tracings={traceback.format_exc()}")

    def httpsave(self):
        headers = {'Content-Type': 'application/json', 'X-Signature': f'{_APPLICATION} {_SWVERSION} ({NODEID})'}
        endpoints = HTTPCDR_ENDPOINTS; shuffle(endpoints)
        cdrjson = json.dumps(self.cdrdata)
        status = 0; attempt = 0
        for endpoint in endpoints:
            attempt += 1; start = time.time()
            try:
                response = requests.post(endpoint, headers=headers, data=cdrjson, timeout=10, )
                status = response.status_code
                if status==200:
                    shortcdr = {'uuid': self.cdrdata.get('uuid'), 'seshid': self.cdrdata.get('seshid')}
                    end = time.time()
                    logify(f"module=liberator, space=cdr, class=CDRHandler, action=httpsave, nodeid={NODEID}, endpoint={endpoint}, status={status}, attempt={attempt}, shortcdr={shortcdr}, delay={round(end-start, 3)}")
                    break
            except Exception as e: # once exception occurred, log the error then retry
                logify(f"module=liberator, space=cdr, class=CDRHandler, action=httpsave, nodeid={NODEID}, endpoint={endpoint}, status={status}, attempt={attempt}, exception={e}, tracings={traceback.format_exc()}")
        # return result
        if status==200: return True
        else: return False

    def rclean(self):
        try:
            rdbconn = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD, decode_responses=True)
            pipe = rdbconn.pipeline()
            pipe.zrem('cdr:inprogress', self.uuid)
            pipe.delete(f'cdr:detail:{self.uuid}')
            pipe.execute()
            result = True
        except Exception as e:
            logify(f"module=liberator, space=cdr, class=CDRHandler, action=rclean, exception={e}, tracings={traceback.format_exc()}")
            result = False
        finally:
            return result


class CDRMaster(Thread):
    def __init__(self):
        self.stop = False
        Thread.__init__(self)
        self.setName('CDRMaster')

    def run(self):
        logify(f"module=liberator, space=cdr, action=start_cdr_thread")
        rdbconn = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWORD, decode_responses=True)
        while not self.stop:
            try:
                reply = rdbconn.blpop('cdr:queue:new', REDIS_TIMEOUT)
                if reply:
                    uuid = reply[1]
                    score = int(time.time())
                    rdbconn.zadd('cdr:inprogress', {uuid: score})
                    detail_key = f'cdr:detail:{uuid}'
                    detail_value = rdbconn.get(detail_key)
                    if detail_value:
                        details = json.loads(detail_value)
                        # write cdr
                        handler = CDRHandler(uuid, details)
                        handler.start()
            except redis.RedisError as e:
                # wait and try again
                time.sleep(5)
            except Exception as e:
                logify(f"module=liberator, space=cdr, class=CDRMaster, action=run, exception={e}, tracings={traceback.format_exc()}")
                time.sleep(2)
            finally: pass

