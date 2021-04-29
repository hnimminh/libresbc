dofile("configuration.lua")
dofile("utilities.lua")
---------------------------------------------------------------------------

local function cdrreporter(event_name, event)
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
        logify('module', 'callflow', 'space', 'events', 'action', 'cdrreporter', 'error', 'rdb.timeout', 'data', cdrjson, 'donext', 'append_to_file', 'filename', filename)
        writefile(filename, cdrjson)
    end
end

local function peer_capacity_handler(event_name, event)
    local uuid = event:getHeader("Unique-ID")
    local direction = event:getHeader("Call-Direction")
    local sofia_profile_name = event:getHeader("variable_sofia_profile_name")
    local sip_network_ip = event:getHeader("variable_sip_network_ip")
    local sip_req_host = event:getHeader("variable_sip_req_host")
    local remote_ip
    if sip_network_ip then remote_ip = sip_network_ip
    else remote_ip = sip_req_host end
    if not remote_ip then remote_ip = 'undefined' end
    -----
    local peername = nil

    -- CHANNEL OCCUPIED EVENT
    if event_name == 'CHANNEL_CREATE' then
        if direction == _INBOUND then
            peername = inbound_peer_recognition(sofia_profile_name, sip_network_ip)
            -- PEER RECOGNITION:
            -- This process performed in CHANNEL_CREATE
            -- & must be effect before CHANNEL_PROGRESS
            -- But NOTHING can guarantee, So not use this mechanism
            -- if peername then fsapi:execute('uuid_setvar', uuid..' variable_V-LIBRE-PEER '..peername) end
        else
            peername = event:getHeader("variable_V-LIBRE-PEER")
        end

        if peername then
            rdbconn:sadd(get_key_peer_node_capacity(peername), uuid)
        else
            logify('module', 'callflow', 'space', 'events', 'action', 'peer_capacity_handler', 'error', 'unrecognize.traffic', 
                   'event', 'channel.create', 'uuid', uuid, 'interface', sofia_profile_name, 'direction', direction, 'remote_ip', remote_ip)
        end
    end

    -- CHANNEL CHANGE UUID EVENT
    if event_name == 'CHANNEL_UUID' then
        peername = event:getHeader("variable_V-LIBRE-PEER")
        local old_uuid = event:getHeader("Old-Unique-ID")
        logify('module', 'callflow', 'space', 'events', 'action', 'peer_capacity_handler', 'event', 'channel.uuid', 'uuid', uuid, 'old_uuid', old_uuid)
        if peername and old_uuid then
            rdbconn:pipeline(function(p)
                p:srem(get_key_peer_node_capacity(peername), old_uuid)
                p:sadd(get_key_peer_node_capacity(peername), uuid)
            end)
        else
            logify('module', 'callflow', 'space', 'events', 'action', 'peer_capacity_handler', 'error', 'unrecognize.traffic', 
                   'event', 'channel.uuid', 'uuid', uuid, 'interface', sofia_profile_name, 'direction', direction, 'remote_ip', remote_ip)
        end
    end

    -- CHANNEL RELEASED EVENT
    if event_name == 'CHANNEL_DESTROY' then
        -- in some case like dead_gateway/invalid_gateway was dialed. 
        -- the is no channel_create envent fired, but still have destroy channel
        -- that case make that peer was not able to recognize and not effect to capacity
        peername = event:getHeader("variable_V-LIBRE-PEER")
        -- best effort to get inbound peername
        if (direction == _INBOUND) and (not peername) then
            peername = inbound_peer_recognition(sofia_profile_name, sip_network_ip)
        end
        if peername then
            rdbconn:srem(get_key_peer_node_capacity(peername), uuid)
        end
    end
end

---------------------******************************---------------------
---------------------*****|      EVENTCTL    |*****---------------------
---------------------******************************---------------------

local function main()
    local event_name = event:getHeader("Event-Name")
    -- local uuid = event:getHeader("Unique-ID"); dlogify('module', 'callflow', 'space', 'events', 'action', 'debug', 'event', event_name, 'uuid', uuid)
    -- PEER CAPACITY HANDLE
    if event_name=='CHANNEL_CREATE' or event_name=='CHANNEL_UUID' or event_name=='CHANNEL_DESTROY' then
        peer_capacity_handler(event_name, event)
    end

    -- CDR HANDLE
    if event_name == 'CHANNEL_HANGUP_COMPLETE' then
        cdrreporter(event_name, event)
    end
end

---------------------******************************---------------------
---------------------*****|       MAIN       |*****---------------------
---------------------******************************---------------------
local result, error = pcall(main)
if not result then
    logger("module=callctl, space=events, action=exception, error="..tostring(error))
end
---- close log ----
syslog.closelog()