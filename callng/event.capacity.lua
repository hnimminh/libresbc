--
-- callng:event.capacity.lua
--
-- The Initial Developer of the Original Code is
-- Minh Minh <hnimminh at[@] outlook dot[.] com>
-- Portions created by the Initial Developer are Copyright (C) the Initial Developer.
-- All Rights Reserved.
--

require("callng.utilities")
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
            intcon = event:getHeader("variable_X-LIBRE-INTCONNAME")
        end
        log.debug('module=callng, space=event:capacity, event_name=channel.create, intcon=%s, direction=%s', intcon, direction)
        if intcon then
            rdbconn:sadd(concurentcallskey(intcon, direction), uuid)
        else
            local profilename = event:getHeader("variable_sofia_profile_name")
            local sip_network_ip = event:getHeader("variable_sip_network_ip")
            local sip_req_host = event:getHeader("variable_sip_req_host")
            log.info('module=callng, space=event:capacity, action=capacity_handler, error=unrecognize_traffic, event=channel.create, '..
                'uuid=%s, profilename=%s, direction=%s, sip_network_ip=%s, sip_req_host=%s', uuid, profilename, direction, sip_network_ip, sip_req_host)
        end
    end

    -- CHANNEL CHANGE UUID EVENT
    if event_name == 'CHANNEL_UUID' then
        intcon = event:getHeader("variable_X-LIBRE-INTCONNAME")
        local old_uuid = event:getHeader("Old-Unique-ID")
        log.info('module=callng, space=event:capacity, action=capacity_handler, event=channel.uuid, uuid=%s, old_uuid=%s', uuid, old_uuid)
        if intcon and old_uuid then
            rdbconn:pipeline(function(p)
                p:srem(concurentcallskey(intcon, direction), old_uuid)
                p:sadd(concurentcallskey(intcon, direction), uuid)
            end)
        else
            local profilename = event:getHeader("variable_sofia_profile_name")
            local sip_network_ip = event:getHeader("variable_sip_network_ip")
            local sip_req_host = event:getHeader("variable_sip_req_host")
            log.info('module=callng, space=event:capacity, action=capacity_handler, error=unrecognize_traffic, event=channel.uuid, '..
                'uuid=%s, profilename=%s, direction=%s, sip_network_ip=%s, sip_req_host=%s', uuid, profilename, direction, sip_network_ip, sip_req_host)
        end
    end

    -- CHANNEL RELEASED EVENT
    if event_name == 'CHANNEL_DESTROY' then
        -- in some case like dead_gateway/invalid_gateway was dialed. the is no channel_create envent fired,
        -- but still have destroy channel, that case make that traffic was not able to recognize and not effect to capacity
        if direction == INBOUND then
            intcon = event:getHeader("variable_user_name")
        else
            intcon = event:getHeader("variable_X-LIBRE-INTCONNAME")
        end
        log.debug('module=callng, space=event:capacity, action=capacity_handler, event=channel.destroy, intcon=%s, direction=%s', intcon, direction)
        if intcon then
            rdbconn:srem(concurentcallskey(intcon, direction), uuid)
        end
    end
end

---------------------******************************---------------------
---------------------*****|       MAIN       |*****---------------------
---------------------******************************---------------------
local result, error = pcall(capacity_handler)
if not result then
    log.critical("module=callng, space=event:capacity, action=exception, error=%s", error)
end
---- close log ----
syslog.closelog()
