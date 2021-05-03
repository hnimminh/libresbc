dofile("{{rundir}}/callctl/utilities.lua")

---------------------******************************---------------------
---------------------****|  INBOUND CALLCTL   |****---------------------
---------------------******************************---------------------
local function main()
    local _manitables = {}
    local InLeg = session
    local OutLeg
    local sessionid = fsapi:execute('create_uuid')
    --- CALL PROCESSING
    if ( InLeg:ready() ) then
        -- get InLeg variables
        local uuid = InLeg:get_uuid()
        local context = InLeg:getVariable("context")
        local profilename = InLeg:getVariable("sofia_profile_name")
        local sip_from_user = InLeg:getVariable("sip_from_user")
        local destination_number = InLeg:getVariable("destination_number")
        local sip_to_user = InLeg:getVariable("sip_to_user")
        local sip_network_ip = InLeg:getVariable("sip_network_ip")
        local sip_call_id = InLeg:getVariable("sip_call_id")
        local sip_via_protocol = InLeg:getVariable("sip_via_protocol")
        local sip_acl_authed_by = InLeg:getVariable("sip_acl_authed_by")
        local sip_authorized = InLeg:getVariable("sip_authorized")
        local sip_acl_token = InLeg:getVariable("sip_acl_token")
        local domain_name = InLeg:getVariable("domain_name")
        local user_name = InLeg:getVariable("user_name")
        -- log the incoming call request
        logify('module', 'callctl', 'space', 'inbound', 'action', 'inbound-call' , 'uuid', uuid, 'context', context, 'direction', 'inbound', 
               'profilename', profilename, 'sip_from_user', sip_from_user, 'sip_to_user', sip_to_user, 
               'destination_number', destination_number, 'sip_network_ip', sip_network_ip, 'callid', sip_call_id,
               'sip_via_protocol', sip_via_protocol, 'sip_acl_authed_by', sip_acl_authed_by, 'sip_authorized', sip_authorized, 
               'sip_acl_token', sip_acl_token, 'user_name', user_name, 'domain_name', domain_name)

        local intconname = user_name
        -----------------------------------------------------------
        ----- IN LEG
        -----------------------------------------------------------

        InLeg:execute('ring_ready')
        InLeg:setVariable("codec_string", "PCMA,OPUS,PCMU,G729")
        InLeg:execute('pre_answer')
        InLeg:setVariable("ringback", "%(2000,4000,440,480)")
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
