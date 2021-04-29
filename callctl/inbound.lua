syslog = require("posix.syslog")
function logger(msg)
    syslog.openlog('libresbc', syslog.LOG_PID, syslog.LOG_LOCAL6)
    syslog.syslog(syslog.LOG_INFO, msg)
end

function logify(...)
    local arg = {...}
    local message = arg[1]..'='..tostring(arg[2])
    for i=3,#arg,2 do message = message..', '..arg[i]..'='..tostring(arg[i+1]) end 
    -- write log
    logger(message)
end

---------------------******************************---------------------
---------------------*****|    CALLFLOWCTL   |*****---------------------
---------------------******************************---------------------
local function main()
    local legIN = session
    local _LOCALS = {}
    --- CALL PROCESSING
    if ( legIN:ready() ) then
        -- get legIN variables
        local in_uuid = legIN:get_uuid()
        local in_context = legIN:getVariable("context")
        local in_direction = legIN:getVariable("direction")
        local in_sofia_profile_name = legIN:getVariable("sofia_profile_name")
        local in_sip_from_user = legIN:getVariable("sip_from_user")
        local in_destination_number = legIN:getVariable("destination_number")
        local in_sip_to_user = legIN:getVariable("sip_to_user")
        local in_sip_network_ip = legIN:getVariable("sip_network_ip")
        local in_sip_call_id = legIN:getVariable("sip_call_id")
        local sip_via_protocol = legIN:getVariable("sip_via_protocol")
        local sip_acl_authed_by = legIN:getVariable("sip_acl_authed_by")
        local sip_authorized = legIN:getVariable("sip_authorized")
        local sip_acl_token = legIN:getVariable("sip_acl_token")
        local domain_name = legIN:getVariable("domain_name")
        local user_name = legIN:getVariable("user_name")
        -- logging
        logify('module', 'callctl', 'space', 'inbound', 'action', 'inbounnd_call_request' , 'uuid', in_uuid,
               'context', in_context, 'direction', in_direction, 'interface', in_sofia_profile_name, 'from_user', in_sip_from_user,
               'to_user', in_sip_to_user, 'destination_number', in_destination_number, 'remote_ip', in_sip_network_ip, 'callid', in_sip_call_id,
               'sip_via_protocol', sip_via_protocol, 'sip_acl_authed_by', sip_acl_authed_by, 'sip_authorized', sip_authorized, 
               'sip_acl_token', sip_acl_token, 'user_name', user_name, 'domain_name', domain_name)
        -----------------------------------------------------------
        ----- IN LEG
        -----------------------------------------------------------
        
        legIN:execute('ring_ready')
        legIN:setVariable("ringback", "%(2000,4000,440,480)")
        legIN:setVariable("codec_string", "PCMA,OPUS,PCMU,G729")
        legIN:execute('playback', '/home/hnimminh/ulaw08m.wav')
        legIN:execute("sleep", "8000")
        legIN:execute('answer')
        legIN:execute('playback', '/home/hnimminh/vietnamdeclaration.wav')
        legIN:execute('hangup')

    end
    ----------------------------------------------------------

    
    if legIN then 
        if (legIN:ready()) then 
            legIN:hangup(); 
        end; 
    end
    if legOUT then 
        if (legOUT:ready()) then 
            legOUT:hangup(); 
        end; 
    end
end


---------------------******************************---------------------
---------------------*****|       MAIN       |*****---------------------
---------------------******************************---------------------
local result, error = pcall(main)
if not result then
    logify("module=callctl, space=inbound,  action=exception, error="..tostring(error))
end
---- close log ----
syslog.closelog()