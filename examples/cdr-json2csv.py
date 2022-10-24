#!/usr/bin/env python3
from sys import argv
import traceback
from datetime import datetime
import json


_COMMA_ = ','
_EMPTY_ = ''

def csvheader():
    return _COMMA_.join([
        'seshid', 'call-id', 'direction', 'peer', 'caller_number', 'destination_number',
        'start_time', 'answer_time', 'end_time', 'conversation_duration (s)', 'session_duration (s)',
        'farend_ipaddr', 'sbc_ipadd', 'status_code', 'released_by', '\n'])

def csvline(cdrs):
    try:
        seshid = cdrs.get('seshid')
        callid = cdrs.get('callid')
        direction = cdrs.get('direction')
        peer = cdrs.get('intconname')
        caller_number = cdrs.get('caller_number')
        destination_number = cdrs.get('destination_number')
        start_time = cdrs.get('start_time')
        start_timestamp = _EMPTY_
        if start_time and start_time != '0':
            start_timestamp = str(datetime.fromtimestamp(int(start_time)))

        answer_time = cdrs.get('answer_time')
        answer_timestamp = _EMPTY_
        if answer_time and answer_time != '0':
            answer_timestamp = str(datetime.fromtimestamp(int(answer_time)))

        end_time = cdrs.get('end_time')
        end_timestamp = _EMPTY_
        if end_time and end_time != '0':
            end_timestamp = str(datetime.fromtimestamp(int(end_time)))

        conversation_duration = cdrs.get('duration')
        session_duration = _EMPTY_
        if end_time and end_time and end_time.isdigit() and start_time.isdigit():
            session_duration = str(int(end_time) - int(start_time))

        sip_network_ip = cdrs.get('sip_network_ip')
        sip_local_network_addr = cdrs.get('sip_local_network_addr')

        sip_hangup_cause = cdrs.get('sip_hangup_cause')
        if not sip_hangup_cause:
            sip_hangup_cause = cdrs.get('bridge_sip_hangup_cause')
        if sip_hangup_cause:
            status_code = sip_hangup_cause[4:]
        else:
            status_code = _EMPTY_
        hangup_disposition = cdrs.get('hangup_disposition')
        if direction == 'outbound':
            if hangup_disposition == 'rev_bye':
                released_by = 'callee'
            else:
                released_by = 'caller'
        else:
            if hangup_disposition == 'rev_bye':
                released_by = 'caller'
            else:
                released_by = 'callee'

        record = [
            seshid, callid, direction, peer, caller_number, destination_number,
            start_timestamp, answer_timestamp, end_timestamp, conversation_duration, session_duration,
            sip_network_ip, sip_local_network_addr, status_code, released_by, '\n']

        return _COMMA_.join(map(str, record))
    except Exception as e:
        print(f'[error] \ncdrs={cdrs}, \nexception={e}, traceback={traceback.format_exc()}')


def run(jsonfile, csvfile=None):
    if not csvfile:
        csvfile = f'{jsonfile[:-5]}.csv'

    with open(jsonfile, 'r') as reader, open(csvfile, 'w') as writer:
        begin = True
        for line in reader.readlines():
            if begin:
                hdr = csvheader()
                writer.writelines(hdr)
                begin = False
            cdr = json.loads(line)
            row = csvline(cdr)
            writer.writelines(row)


if __name__ == '__main__':
    if len(argv) == 2:
        run(jsonfile=str(argv[1]))
    elif len(argv) == 3:
        run(jsonfile=str(argv[1]), csvfile=str(argv[2]))
    else:
        print("[error] please input jsonfile that you want to convert to csv format")
