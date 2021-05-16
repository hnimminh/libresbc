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
        InLeg:execute("export", "X-LIBRE-SESSIONID="..sessionid)
        InLeg:setVariable("X-LIBRE-INTCONNAME", intconname)
        InLeg:setVariable("rtp_secure_media", "optional:"..ENCRYPTION_SUITES)

        -- call will be reject if inbound interconnection is not enable
        local status = is_intcon_enable(intconname, INBOUND)
        if not status then
            logify('module', 'callctl', 'space', 'inbound', 'sessionid', sessionid, 'action', 'state_check' , 'uuid', uuid, 'intconname', intconname, 'status', status)
            INLEG_HANGUP_CAUSE = 'CHANNEL_UNACCEPTABLE'; LIBRE_HANGUP_CAUSE = 'DISABLED_PEER'; goto ENDSESSION
        end

        -- call will be reject if inbound interconnection reach max capacity
        local concurentcalls, max_concurentcalls =  verify_concurentcalls(intconname, INBOUND, uuid)
        logify('module', 'callctl', 'space', 'inbound', 'sessionid', sessionid, 'action', 'concurency_check' , 'uuid', uuid, 'intconname', intconname, 'concurentcalls', concurentcalls, 'max_concurentcalls', max_concurentcalls)
        if concurentcalls > max_concurentcalls then
            INLEG_HANGUP_CAUSE = 'CALL_REJECTED'; LIBRE_HANGUP_CAUSE = 'VIOLATE_MAX_CONCURENT_CALL'; goto ENDSESSION
        end

        -- call will be blocked if inbound interconnection is violated the cps
        local is_passed, current_cps, max_cps, block_ms = verify_cps(intconname, INBOUND, uuid)
        logify('module', 'callctl', 'space', 'inbound', 'sessionid', sessionid, 'action', 'cps_check' ,'uuid', uuid, 'intconname', intconname, 'result', is_passed, 'current_cps', current_cps, 'max_cps', max_cps, 'block_ms', block_ms)
        if not is_passed then
            INLEG_HANGUP_CAUSE = 'CALL_REJECTED'; LIBRE_HANGUP_CAUSE = 'CPS_VIOLATION'; goto ENDSESSION
        end

        -- codec negotiation
        local codecstr = get_codec(intconname, INBOUND)
        InLeg:setVariable("codec_string", codecstr)

        -- translation calling party number
        local tablename = InLeg:getVariable("x-routing-plan")
        routingdata = {tablename=tablename, intconname=intconname, called_number=_dnis, calling_number=_clid}
        route1, route2, routingrules = routing_query(tablename, routingdata)

        local routingrulestr = 'no.matching.route.found'
        if (#routingrules > 0) then routingrulestr = join(routingrules) end
        
        logify('module', 'callctl', 'space', 'inbound', 'sessionid', sessionid, 'action', 'routing_query', 'uuid', uuid, 'routingdata', json.encode(routingdata), 'route1', route1, 'route2', route2, 'routingrules', routingrulestr)
        if not (route1 and route2) then
            INLEG_HANGUP_CAUSE = 'NO_ROUTE_DESTINATION'; LIBRE_HANGUP_CAUSE = 'ROUTE_NOT_FOUND'; goto ENDSESSION    -- SIP 404 NO_ROUTE_DESTINATION
        end

        -- blocking call checking
        if (route1 == BLOCK) or (route2 == BLOCK) then
            logify('module', 'callctl', 'space', 'inbound', 'sessionid', sessionid, 'action', 'hangup_as_block', 'uuid', uuid)
            INLEG_HANGUP_CAUSE = 'CALL_REJECTED'; CUSTOM_HANGUP_CAUSE = 'BLOCK_CALL'; goto ENDSESSION  -- SIP 603 Decline
        end

        --------------------------------------------------------------------
        ----- PRESETTING
        --------------------------------------------------------------------
        InLeg:execute("export", "sip_copy_custom_headers=false")
        -- InLeg:execute("export", "media_timeout=".._MAX_SILENT_TIMEOUT)
        -- Keeping processe dialplan even called party is unreachable
        InLeg:setVariable("continue_on_fail", "true")
        InLeg:setVariable("hangup_after_bridge", "true")
        --
        InLeg:setVariable("call_timeout", "0")
        InLeg:setVariable("fax_enable_t38", "true")
        -- MAX DURATION CALL
        -- InLeg:execute("sched_hangup", "+"..MAX_CALL_DURATION.." allotted_timeout")
        --------------------------------------------------------------------
        ----- OUTLEG
        --------------------------------------------------------------------
        local _uuid
        local routes = {route1, route2}
        for attempt=1, #routes do
            _uuid = fsapi:execute('create_uuid')
            local route = routes[attempt]
            -- distributes calls to gateways in a weighted base
            local forceroute = false 
            local sipprofile = get_sipprofile(route, OUTBOUND)
            local gateway = fsapi:execute('expand', 'distributor '..route..' ${sofia profile '..sipprofile..' gwlist down}')
            if gateway == '-err' then
                gateway = fsapi:execute('distributor', route)
                forceroute = true
            end

            -- set variable on outbound leg 
            InLeg:execute("export", "media_mix_inbound_outbound_codecs=true")
            local outcodecstr = get_codec(route, OUTBOUND)
            InLeg:execute("export", "nolocal:sip_cid_type=none")
            InLeg:execute("export", "nolocal:absolute_codec_string="..outcodecstr)
            --InLeg:execute("export", "nolocal:origination_caller_id_name="..translated_out_clid)
            --InLeg:execute("export", "nolocal:origination_caller_id_number="..translated_out_clid)
            InLeg:execute("export", "nolocal:originate_timeout=90")
            InLeg:execute("export", "nolocal:fax_enable_t38=true")
            InLeg:execute("export", "nolocal:hangup_after_bridge=true")
            InLeg:execute("export", "nolocal:origination_uuid=".._uuid)
            InLeg:execute("export", "nolocal:sip_h_X-LIBRE-ORIGIN-HOP="..intconname)
            InLeg:setVariable("sip_ph_X-LIBRE-NEXT-HOP", route)
            InLeg:setVariable("sip_rh_X-LIBRE-NEXT-HOP", route)
            InLeg:execute("export", "nolocal:X-LIBRE-INTCONNAME="..route)
            -- RTP/SRTP DECISION
            --InLeg:execute("export", "nolocal:rtp_secure_media=optional:".._encryption_suites)
            --InLeg:setVariable("sdp_secure_savp_only", "true")
            
            logify('module', 'callctl', 'space', 'inbound', 'action', 'connect_gateway' , 'sessionid', sessionid, 'uuid', _uuid, 'route', route, 'sipprofile', sipprofile, 'gateway', gateway, 'forceroute', forceroute)
            OutLeg = freeswitch.Session("sofia/gateway/"..gateway.."/"..destination_number, InLeg)

            -- check leg status
            local dialstatus = OutLeg:hangupCause()
            logify('module', 'callctl', 'space', 'inbound', 'action', 'verify_state' , 'sessionid', sessionid, 'uuid', _uuid, 'attempt', attempt, 'status', dialstatus)

            -- stop if success
            if (ismeberof({'SUCCESS', 'NO_ANSWER', 'USER_BUSY', 'NORMAL_CLEARING', 'ORIGINATOR_CANCEL'}, dialstatus)) then
                break
            end
            ::ENDROUTING::
        end

        -- sleep to make sure channel available
        InLeg:sleep(500)

        if OutLeg then 
            if( OutLeg:ready() ) then
                -- log information for leg B
                local _real_uuid = OutLeg:get_uuid()
                if _uuid ~= _real_uuid then
                    logify('module', 'callctl', 'space', 'inbound', 'sessionid', sessionid, 'action', 'report', 'pseudo_uuid', _uuid, 'native_uuid', _real_uuid)
                end
                local _context = OutLeg:getVariable("context")
                local _direction = OutLeg:getVariable("direction")
                local _sip_from_user = OutLeg:getVariable("sip_from_user")
                local _sip_req_uri = OutLeg:getVariable("sip_req_uri")
                local _destination_number = OutLeg:getVariable("destination_number")
                local _sip_to_user = OutLeg:getVariable("sip_to_user")
                local _sip_network_ip = OutLeg:getVariable("sip_network_ip")
                local _sofia_profile_name = OutLeg:getVariable("sofia_profile_name")
                local _sip_call_id = OutLeg:getVariable("sip_call_id")

                logify('module', 'callctl', 'space', 'inbound', 'sessionid', sessionid, 'action', 'report', 'uuid', _real_uuid,
                       'context', _context, 'direction', _direction, 'sipprofile', _sofia_profile_name, 'ruri', _sip_req_uri, 'from_user', _sip_from_user, 
                       'to_user', _sip_to_user, 'destination_number', _destination_number, 'remote_ip', _sip_network_ip, 'callid', _sip_call_id)
                
                --- BRIDGE 2 LEGs
                logify('module', 'callctl', 'space', 'inbound', 'sessionid', sessionid, 'action', 'bridge' , 'inbound_uuid', uuid, 'outbound_uuid', _real_uuid)
                freeswitch.bridge(InLeg, OutLeg)

                -- HANGUP WHEN DONE FOR OUTLEG
                if (OutLeg:ready()) then 
                    OutLeg:hangup(); 
                end
            else
                logify('module', 'callctl', 'space', 'inbound', 'sessionid', sessionid, 'action', 'report', 'info', 'outbound.leg.not.connected')
            end
        end

        -----------------------------------------------------------
        ----- TMP
        -----------------------------------------------------------
        --[[]
        InLeg:execute('ring_ready')
        InLeg:execute('pre_answer')
        InLeg:setVariable("ringback", "%(2000,4000,440,480)")
        InLeg:execute('playback', '/home/hnimminh/ulaw08m.wav')
        InLeg:execute("sleep", "8000")
        InLeg:execute('answer')
        InLeg:execute('playback', '/home/hnimminh/vietnamdeclaration.wav')
        InLeg:execute('hangup')
        ]]

        -----------------------------------------------------------
        --- HANGUP ONCE DONE
        -----------------------------------------------------------
        if (InLeg:ready()) then 
            InLeg:setVariable("X-LIBRE-HANGUP-CAUSE", LIBRE_HANGUP_CAUSE)
            InLeg:hangup(INLEG_HANGUP_CAUSE); 
        end
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
