--
-- callng:event.cdr.lua
-- 
-- The Initial Developer of the Original Code is
-- Minh Minh <hnimminh@outlook.com>
-- Portions created by the Initial Developer are Copyright (C) the Initial Developer. 
-- All Rights Reserved.
--

dofile("{{rundir}}/callng/utilities.lua")
---------------------------------------------------------------------------

local function cdrreport()
    local uuid = event:getHeader("Unique-ID")
    local seshid = event:getHeader("variable_X-LIBRE-SESHID")
    local direction = event:getHeader("Call-Direction")
    local sipprofile = event:getHeader("variable_sofia_profile_name")
    local context = event:getHeader("Caller-Context")
    local intconname = event:getHeader("variable_X-LIBRE-INTCONNAME")
    local gateway_name = event:getHeader("variable_sip_gateway_name")
    local user_agent = event:getHeader("variable_sip_user_agent")
    local callid = event:getHeader("variable_sip_call_id")
    local caller_name = event:getHeader("Caller-Caller-ID-Name")
    local caller_number = event:getHeader("Caller-Caller-ID-Number")
    local destination_number = event:getHeader("Caller-Destination-Number")
    --
    local start_time = event:getHeader("variable_start_epoch")
    local answer_time = event:getHeader("variable_answer_epoch")
    local end_time = event:getHeader("variable_end_epoch")
    local duration = event:getHeader("variable_billsec")
    --
    local sip_network_ip = event:getHeader("variable_sip_network_ip")
    local sip_network_port = event:getHeader("variable_sip_network_port")
    local sip_local_network_addr  = event:getHeader("variable_sip_local_network_addr")
    local sip_via_protocol = event:getHeader("variable_sip_via_protocol")
    local sip_req_uri = event:getHeader("variable_sip_req_uri") -- variable_sip_destination_url sip:84987654321@libre.io:5060;transport=udp
    --
    local remote_media_ip = event:getHeader("variable_remote_media_ip") 
    local remote_media_port = event:getHeader("variable_remote_media_port")
    local local_media_ip = event:getHeader("variable_local_media_ip")
    local local_media_port = event:getHeader("variable_local_media_port")
    local advertised_media_ip = event:getHeader("variable_advertised_media_ip")
    local read_codec = event:getHeader("variable_read_codec") 
    local write_codec = event:getHeader("variable_write_codec") 
    --
    local hangup_disposition = event:getHeader('variable_sip_hangup_disposition')
    local hangup_cause = event:getHeader("variable_hangup_cause")
    local libre_hangup_cause = event:getHeader("variable_X-LIBRE-HANGUP-CAUSE")
    local sip_hangup_cause = event:getHeader("variable_proto_specific_hangup_cause")
    local bridge_sip_hangup_cause = event:getHeader("variable_last_bridge_proto_specific_hangup_cause")
    local libre_sip_hangup_cause = event:getHeader("variable_X-LIBRE-SIP-HANGUP-CAUSE")
    local sip_redirected_to = event:getHeader("variable_sip_redirected_to")
    local rtp_has_crypto = event:getHeader("variable_rtp_has_crypto")
    --
    cdr_details = {
        uuid=uuid, 
        seshid=seshid, 
        direction=direction,
        sipprofile=sipprofile,
        context=context,
        nodeid=NODEID,
        intconname=intconname,
        gateway_name=gateway_name,
        user_agent=user_agent,
        callid=callid,
        caller_name=caller_name,
        caller_number=caller_number,
        destination_number=destination_number,
        start_time=start_time,
        answer_time=answer_time,
        end_time=end_time,
        duration=duration,
        sip_network_ip=sip_network_ip,
        sip_network_port=sip_network_port,
        sip_local_network_addr=sip_local_network_addr,
        sip_via_protocol=sip_via_protocol,
        sip_req_uri=sip_req_uri,
        remote_media_ip=remote_media_ip,
        remote_media_port=remote_media_port,
        local_media_ip=local_media_ip,
        local_media_port=local_media_port,
        advertised_media_ip=advertised_media_ip,
        read_codec=read_codec,
        write_codec=write_codec,
        hangup_disposition=hangup_disposition,
        hangup_cause=hangup_cause,
        libre_hangup_cause=libre_hangup_cause,
        sip_hangup_cause=sip_hangup_cause,
        bridge_sip_hangup_cause=bridge_sip_hangup_cause,
        libre_sip_hangup_cause=libre_sip_hangup_cause,
        sip_redirected_to=sip_redirected_to,
        rtp_has_crypto=rtp_has_crypto
    }

    -- push raw cdr to redis, may use "event:serialize('json')" if needed
    cdrjson = json.encode(cdr_details)
    if rdbstate then
        rdbconn:pipeline(function(pipe)
            pipe:rpush('cdr:queue:new', uuid)
            pipe:setex('cdr:detail:'..uuid, CDRTTL, cdrjson)
        end)
    else 
        filename = os.date("%Y-%m-%d")..'.cdr.raw.json'
        writefile(LOGDIR..'/cdr/'..filename, cdrjson)
        logify('module', 'callng', 'space', 'event:cdr', 'action', 'cdrreporter', 'error', 'rdbtimeout', 'data', cdrjson, 'donext', 'writefile', 'filename', filename)
    end
end

---------------------******************************---------------------
---------------------*****|       MAIN       |*****---------------------
---------------------******************************---------------------
local result, error = pcall(cdrreport)
if not result then
    logger("module=callng, space=event:cdr, action=exception, error="..tostring(error))
end
---- close log ----
syslog.closelog()
