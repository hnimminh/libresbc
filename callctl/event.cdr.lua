dofile("{{rundir}}/callctl/utilities.lua")
---------------------------------------------------------------------------

local function cdrreporter()
    local uuid = event:getHeader("Unique-ID")
    local seshid = event:getHeader("variable_V-LIBRE-SESHID")
    local direction = event:getHeader("Call-Direction")
    local interface = event:getHeader("variable_sofia_profile_name")
    local nodename = event:getHeader("FreeSWITCH-Hostname")
    --
    local peername = event:getHeader("variable_V-LIBRE-PEER")
    local user_agent = event:getHeader("variable_sip_user_agent")
    local callid = event:getHeader("variable_sip_call_id")
    local caller = event:getHeader("Caller-Caller-ID-Number")
    local callee = event:getHeader("Caller-Destination-Number")
    --
    local start_time = event:getHeader("variable_start_epoch")
    local answer_time = event:getHeader("variable_answer_epoch")
    local end_time = event:getHeader("variable_end_epoch")
    local duration = event:getHeader("variable_billsec")
    --
    local network_ip = event:getHeader("variable_sip_network_ip")
    local network_port = event:getHeader("variable_sip_network_port")
    local to_host = event:getHeader("variable_sip_to_host")
    local to_port = event:getHeader("variable_sip_to_port")
    local local_ip = event:getHeader("FreeSWITCH-IPv4")
    local local_network_addr  = event:getHeader("variable_sip_local_network_addr")
    local transport = event:getHeader("variable_V-LIBRE-TRANSPORT") 
    --
    local remote_media_ip = event:getHeader("variable_remote_media_ip") 
    local remote_media_port = event:getHeader("variable_remote_media_port")
    local local_media_ip = event:getHeader("variable_local_media_ip")
    local local_media_port = event:getHeader("variable_local_media_port")
    local read_codec = event:getHeader("variable_read_codec") 
    local write_codec = event:getHeader("variable_write_codec") 

    --
    local hangup_disposition = event:getHeader('variable_sip_hangup_disposition')
    local hangup_cause = event:getHeader("variable_hangup_cause")
    local custom_hangup_cause = event:getHeader("variable_V-LIBRE-CUSTOM-HANGUP-CAUSE")
    local sip_hangup_cause = event:getHeader("variable_proto_specific_hangup_cause")
    local bridge_sip_hangup_cause = event:getHeader("variable_last_bridge_proto_specific_hangup_cause")
    local custom_sip_hangup_cause = event:getHeader("variable_V-LIBRE-CUSTOM-SIP-HANGUP-CAUSE")
    local sip_redirected_to = event:getHeader("variable_sip_redirected_to")
    local rtp_has_crypto = event:getHeader("variable_rtp_has_crypto")
    local correlation_id = event:getHeader("variable_V-LIBRE-CORRELATION-ID")
    --
    cdr_details = {
        uuid=uuid, 
        seshid=seshid, 
        direction=direction, 
        interface=interface, 
        nodename=nodename, 
        peername=peername,
        user_agent=user_agent, 
        callid=callid, 
        caller=caller, 
        callee=callee, 
        start_time=start_time, 
        answer_time=answer_time, 
        end_time=end_time, 
        duration=duration, 
        network_ip=network_ip, 
        network_port=network_port, 
        to_host=to_host, 
        to_port=to_port,
        local_ip=local_ip, 
        local_network_addr=local_network_addr, 
        transport=transport, 
        remote_media_ip=remote_media_ip, 
        remote_media_port=remote_media_port, 
        local_media_ip=local_media_ip, 
        local_media_port=local_media_port, 
        read_codec=read_codec,
        write_codec=write_codec,
        hangup_disposition=hangup_disposition, 
        hangup_cause=hangup_cause, 
        custom_hangup_cause=custom_hangup_cause,
        sip_hangup_cause=sip_hangup_cause, 
        bridge_sip_hangup_cause=bridge_sip_hangup_cause,
        custom_sip_hangup_cause=custom_sip_hangup_cause,
        sip_redirected_to=sip_redirected_to, 
        rtp_has_crypto=rtp_has_crypto,
        correlation_id=correlation_id
    }

    -- push raw cdr to redis, may use "event:serialize('json')" if needed
    if rdbstate then
        rdbconn:pipeline(function(p)
            p:rpush('cdr:queue:new', uuid)
            p:setex('cdr:detail:'..uuid, CDR_TTL, json.encode(cdr_details))
        end)
    else 
        filename = os.date("%Y-%m-%d")..'.cdr.raw.json'
        cdrjson = json.encode(cdr_details)
        logify('module', 'callctl', 'space', 'event:cdr', 'action', 'cdrreporter', 'error', 'rdb.timeout', 'data', cdrjson, 'donext', 'append_to_file', 'filename', filename)
        writefile(filename, cdrjson)
    end
end

---------------------******************************---------------------
---------------------*****|       MAIN       |*****---------------------
---------------------******************************---------------------
local result, error = pcall(cdrreporter)
if not result then
    logger("module=callctl, space=event:cdr, action=exception, error="..tostring(error))
end
---- close log ----
syslog.closelog()
