dofile("{{rundir}}/callctl/utilities.lua")

---------------------******************************---------------------
---------------------****|  INBOUND CALLCTL   |****---------------------
---------------------******************************---------------------
local function main()
    local _manitables = {}
    local InLeg = session
    local OutLeg
    --- CALL PROCESSING
    if ( InLeg:ready() ) then
        -- get InLeg variables
        local in_uuid = InLeg:get_uuid()
        local in_context = InLeg:getVariable("context")
        local in_direction = InLeg:getVariable("direction")
        local in_sofia_profile_name = InLeg:getVariable("sofia_profile_name")
        local in_sip_from_user = InLeg:getVariable("sip_from_user")
        local in_destination_number = InLeg:getVariable("destination_number")
        local in_sip_to_user = InLeg:getVariable("sip_to_user")
        local in_sip_network_ip = InLeg:getVariable("sip_network_ip")
        local in_sip_call_id = InLeg:getVariable("sip_call_id")
        local sip_via_protocol = InLeg:getVariable("sip_via_protocol")
        local sip_acl_authed_by = InLeg:getVariable("sip_acl_authed_by")
        local sip_authorized = InLeg:getVariable("sip_authorized")
        local sip_acl_token = InLeg:getVariable("sip_acl_token")
        local domain_name = InLeg:getVariable("domain_name")
        local user_name = InLeg:getVariable("user_name")
        -- logging
        logify('module', 'callctl', 'space', 'inbound', 'action', 'inbounnd_call_request' , 'uuid', in_uuid,
               'context', in_context, 'direction', in_direction, 'interface', in_sofia_profile_name, 'from_user', in_sip_from_user,
               'to_user', in_sip_to_user, 'destination_number', in_destination_number, 'remote_ip', in_sip_network_ip, 'callid', in_sip_call_id,
               'sip_via_protocol', sip_via_protocol, 'sip_acl_authed_by', sip_acl_authed_by, 'sip_authorized', sip_authorized, 
               'sip_acl_token', sip_acl_token, 'user_name', user_name, 'domain_name', domain_name)
        -----------------------------------------------------------
        ----- IN LEG
        -----------------------------------------------------------
        
        InLeg:execute('ring_ready')
        InLeg:setVariable("ringback", "%(2000,4000,440,480)")
        InLeg:setVariable("codec_string", "PCMA,OPUS,PCMU,G729")
        InLeg:execute('playback', '/home/hnimminh/ulaw08m.wav')
        InLeg:execute("sleep", "8000")
        InLeg:execute('answer')
        InLeg:execute('playback', '/home/hnimminh/vietnamdeclaration.wav')
        InLeg:execute('hangup')

    end
    -----------------------------------------------------------
    --- MAKE SURE CALL IS RELAESED
    -----------------------------------------------------------
    if InLeg then 
        if (InLeg:ready()) then InLeg:hangup() end 
    end
    if OutLeg then 
        if (OutLeg:ready()) then OutLeg:hangup() end
    end
    -----------------------------------------------------------

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
