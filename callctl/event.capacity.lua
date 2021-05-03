dofile("{{rundir}}/callctl/utilities.lua")
---------------------------------------------------------------------------

local function capacity_handler()
    local event_name = event:getHeader("Event-Name")
    local uuid = event:getHeader("Unique-ID")
    local direction = event:getHeader("Call-Direction")
    -----
    local intcon = nil

    -- CHANNEL OCCUPIED EVENT
    if event_name == 'CHANNEL_CREATE' then
        if direction == INBOUND then
            intcon = event:getHeader("variable_user_name")
        else
            intcon = event:getHeader("variable_X-LIBRE-INTCON")
        end

        if intcon then
            rdbconn:sadd('realtime:capacity:'..intcon..':'..NODEID, uuid)
        else
            local profilename = event:getHeader("variable_sofia_profile_name")
            local sip_network_ip = event:getHeader("variable_sip_network_ip")
            local sip_req_host = event:getHeader("variable_sip_req_host")
            logify('module', 'callctl', 'space', 'event:capacity', 'action', 'capacity_handler', 'error', 'unrecognize_traffic', 'event', 'channel.create', 
                   'uuid', uuid, 'profilename', profilename, 'direction', direction, 'sip_network_ip', sip_network_ip, 'sip_req_host', sip_req_host)
        end
    end

    -- CHANNEL CHANGE UUID EVENT
    if event_name == 'CHANNEL_UUID' then
        intcon = event:getHeader("variable_X-LIBRE-INTCON")
        local old_uuid = event:getHeader("Old-Unique-ID")
        logify('module', 'callctl', 'space', 'event:capacity', 'action', 'capacity_handler', 'event', 'channel.uuid', 'uuid', uuid, 'old_uuid', old_uuid)
        if intcon and old_uuid then
            rdbconn:pipeline(function(p)
                p:srem('realtime:capacity:'..intcon..':'..NODEID, old_uuid)
                p:sadd('realtime:capacity:'..intcon..':'..NODEID, uuid)
            end)
        else
            local profilename = event:getHeader("variable_sofia_profile_name")
            local sip_network_ip = event:getHeader("variable_sip_network_ip")
            local sip_req_host = event:getHeader("variable_sip_req_host")
            logify('module', 'callctl', 'space', 'event:capacity', 'action', 'capacity_handler', 'error', 'unrecognize_traffic', 'event', 'channel.uuid', 
                   'uuid', uuid, 'profilename', profilename, 'direction', direction, 'sip_network_ip', sip_network_ip, 'sip_req_host', sip_req_host)
        end
    end

    -- CHANNEL RELEASED EVENT
    if event_name == 'CHANNEL_DESTROY' then
        -- in some case like dead_gateway/invalid_gateway was dialed. the is no channel_create envent fired, 
        -- but still have destroy channel, that case make that traffic was not able to recognize and not effect to capacity
        if direction == INBOUND then
            intcon = event:getHeader("variable_user_name")
        else
            intcon = event:getHeader("variable_X-LIBRE-INTCON")
        end

        if intcon then
            rdbconn:srem('realtime:capacity:'..intcon..':'..NODEID, uuid)
        end
    end
end

---------------------******************************---------------------
---------------------*****|       MAIN       |*****---------------------
---------------------******************************---------------------
local result, error = pcall(capacity_handler)
if not result then
    logger("module=callctl, space=event:capacity, action=exception, error="..tostring(error))
end
---- close log ----
syslog.closelog()
