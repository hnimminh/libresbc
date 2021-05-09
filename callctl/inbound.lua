dofile("{{rundir}}/callctl/utilities.lua")
dofile("{{rundir}}/callctl/callfunc.lua")
---------------------******************************---------------------
---------------------****|  INBOUND CALLCTL   |****---------------------
---------------------******************************---------------------
local function main()
    local _manitables = {}
    local InLeg = session
    local OutLeg = nil
    local sessionid = fsapi:execute('create_uuid')
    local ENCRYPTION_SUITES = table.concat(SRPT_ENCRYPTION_SUITES, ':')
    local INLEG_HANGUP_CAUSE = 'NORMAL_CLEARING'
    local LIBRE_HANGUP_CAUSE = 'NONE'
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
        local realm = InLeg:getVariable("domain_name")
        local intconname = InLeg:getVariable("user_name")
        -- log the incoming call request
        logify('module', 'callctl', 'space', 'inbound', 'sessionid', sessionid, 'action', 'inbound-call' , 'uuid', uuid, 'context', context, 'direction', 'inbound', 
               'profilename', profilename, 'sip_from_user', sip_from_user, 'sip_to_user', sip_to_user, 
               'destination_number', destination_number, 'sip_network_ip', sip_network_ip, 'callid', sip_call_id,
               'sip_via_protocol', sip_via_protocol, 'intconname', intconname, 'realm', realm)

        -----------------------------------------------------------
        ---- IN LEG: INTIAL VAR
        -----------------------------------------------------------
        local LIBRE_SIP_TRANSPORT = 'udp'
        if sip_via_protocol then LIBRE_SIP_TRANSPORT = sip_via_protocol:lower() end
        InLeg:setVariable("X-LIBRE-SIP-TRANSPORT", LIBRE_SIP_TRANSPORT)
        InLeg:setVariable("X-LIBRE-INTCON-NAME", intconname)
        InLeg:setVariable("rtp_secure_media", "optional:"..ENCRYPTION_SUITES)


        -- call will be reject if inbound interconnection is not enable
        local status = is_intcon_enable(intconname, INBOUND)
        if not status then
            logify('module', 'callctl', 'space', 'inbound', 'sessionid', sessionid, 'action', 'state_check' ,'intconname', intconname, 'status', status)
            INLEG_HANGUP_CAUSE = 'CHANNEL_UNACCEPTABLE'; LIBRE_HANGUP_CAUSE = 'DISABLED_PEER'; goto ENDSESSION
        end

        -- call will be reject if inbound interconnection reach max capacity
        local concurentcalls, max_concurentcalls =  verify_concurentcalls(intconname, INBOUND, uuid)
        logify('module', 'callctl', 'space', 'inbound', 'sessionid', sessionid, 'action', 'concurency_check' ,'intconname', intconname, 'concurentcalls', concurentcalls, 'max_concurentcalls', max_concurentcalls)
        if concurentcalls > max_concurentcalls then
            INLEG_HANGUP_CAUSE = 'CALL_REJECTED'; LIBRE_HANGUP_CAUSE = 'VIOLATE_MAX_CONCURENT_CALL'; goto ENDSESSION
        end

        -- call will be blocked if inbound interconnection is violated the cps
        local is_passed, current_cps, max_cps, block_ms = verify_cps(intconname, INBOUND, uuid)
        logify('module', 'callctl', 'space', 'inbound', 'sessionid', sessionid, 'action', 'cps_check' ,'intconname', intconname, 'result', is_passed, 'current_cps', current_cps, 'max_cps', max_cps, 'block_ms', block_ms)
        if not is_passed then
            INLEG_HANGUP_CAUSE = 'CALL_REJECTED'; LIBRE_HANGUP_CAUSE = 'CPS_VIOLATION'; goto ENDSESSION
        end




        -----------------------------------------------------------
        ----- TMP
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
    ::ENDSESSION::
    -----------------------------------------------------------
    --- MAKE SURE CALL IS RELAESED
    -----------------------------------------------------------
    if InLeg then 
        if (InLeg:ready()) then 
            InLeg:setVariable("X-LIBRE-HANGUP-CAUSE", LIBRE_HANGUP_CAUSE)
            InLeg:hangup(INLEG_HANGUP_CAUSE) 
        end 
    end
    if OutLeg then 
        if (OutLeg:ready()) then
            OutLeg:setVariable("X-LIBRE-HANGUP-CAUSE", LIBRE_HANGUP_CAUSE)
            OutLeg:hangup() 
        end
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
