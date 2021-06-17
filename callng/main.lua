--
-- callng:main.lua
-- 
-- The Initial Developer of the Original Code is
-- Minh Minh <hnimminh@outlook.com>
-- Portions created by the Initial Developer are Copyright (C) the Initial Developer. All Rights Reserved.
--
--

dofile("{{rundir}}/callng/callfunc.lua")
---------------------******************************---------------------
---------------------****|  INBOUND callng   |****---------------------
---------------------******************************---------------------
local function main()
    local NgVars = {}
    local InLeg = session
    local OutLeg = nil
    local seshid = fsapi:execute('create_uuid')
    local ENCRYPTION_SUITES = table.concat(SRPT_ENCRYPTION_SUITES, ':')
    local HANGUP_CAUSE = 'NORMAL_CLEARING'
    local LIBRE_HANGUP_CAUSE = 'NONE'
    --- CALL PROCESSING
    if ( InLeg:ready() ) then
        -- get InLeg variables
        local uuid = InLeg:get_uuid()
        local context = InLeg:getVariable("context")
        local profilename = InLeg:getVariable("sofia_profile_name")
        local network_ip = InLeg:getVariable("sip_network_ip")
        local realm = InLeg:getVariable("domain_name")
        local intconname = InLeg:getVariable("user_name")
        local call_id = InLeg:getVariable("sip_call_id")
        local transport = InLeg:getVariable("sip_via_protocol")
        local caller_name = InLeg:getVariable("caller_id_name")
        local caller_number = InLeg:getVariable("caller_id_number")
        local destination_number = InLeg:getVariable("destination_number")
        -- log the incoming call request
        logify('module', 'callng', 'space', 'main', 'seshid', seshid, 'action', 'inbound_call' , 'uuid', uuid, 'context', context, 
               'profilename', profilename, 'network_ip', network_ip, 'realm', realm, 'intconname', intconname, 'call_id', call_id,
               'transport', transport, 'caller_name', caller_name, 'caller_number', caller_number, 'destination_number', destination_number)
        -----------------------------------------------------------
        ---- IN LEG: INTIAL VAR
        -----------------------------------------------------------
        InLeg:execute("export", "X-LIBRE-SESHID="..seshid)
        InLeg:setVariable("X-LIBRE-INTCONNAME", intconname)
        -- call will be reject if inbound interconnection is not enable
        if not is_intcon_enable(intconname, INBOUND) then
            logify('module', 'callng', 'space', 'main', 'seshid', seshid, 'action', 'state_check' , 'uuid', uuid, 'intconname', intconname, 'state', 'disabled', 'donext', 'hangup_as_disabled')
            HANGUP_CAUSE = 'CHANNEL_UNACCEPTABLE'; LIBRE_HANGUP_CAUSE = 'DISABLED_CONNECTION'; goto ENDSESSION
        end

        -- call will be reject if inbound interconnection reach max capacity
        local concurentcalls, max_concurentcalls =  verify_concurentcalls(intconname, INBOUND, uuid)
        logify('module', 'callng', 'space', 'main', 'seshid', seshid, 'action', 'concurency_check' , 'uuid', uuid, 'intconname', intconname, 'concurentcalls', concurentcalls, 'max_concurentcalls', max_concurentcalls)
        if concurentcalls > max_concurentcalls then
            HANGUP_CAUSE = 'CALL_REJECTED'; LIBRE_HANGUP_CAUSE = 'MAX_CONCURENT_CALL'; goto ENDSESSION
        end

        -- call will be blocked if inbound interconnection is violated the cps
        local is_passed, current_cps, max_cps, block_ms = verify_cps(intconname, INBOUND, uuid)
        logify('module', 'callng', 'space', 'main', 'seshid', seshid, 'action', 'cps_check' ,'uuid', uuid, 'intconname', intconname, 'result', is_passed, 'current_cps', current_cps, 'max_cps', max_cps, 'block_ms', block_ms)
        if not is_passed then
            HANGUP_CAUSE = 'CALL_REJECTED'; LIBRE_HANGUP_CAUSE = 'MAX_CPS'; goto ENDSESSION
        end
        -- translation
        local clidnum, clidname, dnisnum, tranrules = translate(caller_number, caller_name, destination_number, intconname, INBOUND)
        logify('module', 'callng', 'space', 'main', 'seshid', seshid, 'action', 'translate', 'direction', INBOUND, 'uuid', uuid, 'tranrules', rulejoin(tranrules), 'clidnum', clidnum, 'clidname', clidname, 'dnisnum', dnisnum)
        -- media negotiation
        local codecstr = get_codec(intconname, INBOUND)
        InLeg:setVariable("codec_string", codecstr)
        if transport:lower()=='tls' then
            InLeg:setVariable("rtp_secure_media", "mandatory:"..ENCRYPTION_SUITES)
            InLeg:setVariable("sdp_secure_savp_only", "true")
        end

        -- inbound normalization
        normalize(intconname, DxLeg, NgVars)

        -- routing
        local tablename = InLeg:getVariable("x-routing-plan")
        routingdata = {tablename=tablename, intconname=intconname, caller_number=clidnum, destination_number=dnisnum}
        route1, route2, routingrules = routing_query(tablename, routingdata)

        local routingrulestr = 'no.matching.route.found'
        if (#routingrules > 0) then routingrulestr = rulejoin(routingrules) end
        
        logify('module', 'callng', 'space', 'main', 'seshid', seshid, 'action', 'routing_query', 'uuid', uuid, 'routingdata', json.encode(routingdata), 'route1', route1, 'route2', route2, 'routingrules', routingrulestr)
        if not (route1 and route2) then
            HANGUP_CAUSE = 'NO_ROUTE_DESTINATION'; LIBRE_HANGUP_CAUSE = 'ROUTE_NOT_FOUND'; goto ENDSESSION    -- SIP 404 NO_ROUTE_DESTINATION
        end

        -- blocking call checking
        if (route1 == BLOCK) or (route2 == BLOCK) then
            logify('module', 'callng', 'space', 'main', 'seshid', seshid, 'action', 'hangup_as_block', 'uuid', uuid)
            HANGUP_CAUSE = 'CALL_REJECTED'; CUSTOM_HANGUP_CAUSE = 'BLOCK_CALL'; goto ENDSESSION  -- SIP 603 Decline
        end
        --------------------------------------------------------------------
        if InLeg:getVariable("x-ringready") then InLeg:execute('ring_ready') end
        earlyMediaProcess(intconname, InLeg)
        --------------------------------------------------------------------
        ----- PRESETTING
        --------------------------------------------------------------------
        InLeg:execute("export", "sip_copy_custom_headers=false")
        InLeg:setVariable("continue_on_fail", "true")
        InLeg:setVariable("hangup_after_bridge", "true")
        InLeg:setVariable("call_timeout", "0")
        InLeg:setVariable("fax_enable_t38", "true")
        -- InLeg:execute("export", "media_timeout=".._MAX_SILENT_TIMEOUT)
        -- InLeg:execute("sched_hangup", "+"..MAX_CALL_DURATION.." allotted_timeout")
        --------------------------------------------------------------------
        ----- OUTLEG
        --------------------------------------------------------------------
        local _uuid
        local routes = (route1==route2) and {route1} or {route1, route2}
        for attempt=1, #routes do
            _uuid = fsapi:execute('create_uuid')
            local route = routes[attempt]

            -- if state is disable then try next route or drop call
            if not is_intcon_enable(route, OUTBOUND) then
                logify('module', 'callng', 'space', 'main', 'seshid', seshid, 'action', 'state_check' , 'uuid', _uuid, 'route', route, 'state', 'disabled', 'donext', 'hangup_as_disabled')
                if attempt >= #routes then HANGUP_CAUSE = 'CHANNEL_UNACCEPTABLE'; LIBRE_HANGUP_CAUSE = 'DISABLED_CONNECTION' end; goto ENDFAILOVER
            end

            -- call will be reject if outbound interconnection reach max capacity
            local _concurentcalls, _max_concurentcalls =  verify_concurentcalls(route, OUTBOUND, _uuid)
            logify('module', 'callng', 'space', 'main', 'seshid', seshid, 'action', 'concurency_check' , 'uuid', _uuid, 'route', route, 'concurentcalls', _concurentcalls, 'max_concurentcalls', _max_concurentcalls)
            if _concurentcalls >= _max_concurentcalls then
                if attempt >= #routes then HANGUP_CAUSE = 'CALL_REJECTED'; LIBRE_HANGUP_CAUSE = 'MAX_CONCURENT_CALL' end; goto ENDFAILOVER
            end

            -- call will be reject if outbound interconnection reach max cps
            local waitms, queue, max_cps = average_cps(route, OUTBOUND)
            logify('module', 'callng', 'space', 'main', 'seshid', seshid, 'action', 'average_cps' ,'uuid', _uuid, 'route', route, 'waitms', waitms, 'queue', queue, 'max_cps', max_cps)
            if queue >  max_cps then
                HANGUP_CAUSE = 'CALL_REJECTED'; LIBRE_HANGUP_CAUSE = 'MAX_QUEUE'; goto ENDFAILOVER
            else InLeg:sleep(waitms) end
            
            -- translation
            local _clidnum, _clidname, _dnisnum, _tranrules = translate(clidnum, clidname, dnisnum, route, OUTBOUND)
            logify('module', 'callng', 'space', 'main', 'seshid', seshid, 'action', 'translate', 'direction', OUTBOUND, 'uuid', _uuid, 'tranrules', rulejoin(_tranrules), 'clidnum', _clidnum, 'clidname', _clidname, 'dnisnum', _dnisnum)

            -- distributes calls to gateways in a weighted base
            local forceroute = false 
            local sipprofile = get_sipprofile(route, OUTBOUND)
            local gateway = fsapi:execute('expand', 'distributor '..route..' ${sofia profile '..sipprofile..' gwlist down}')
            if gateway == '-err' then
                gateway = fsapi:execute('distributor', route)
                forceroute = true
            end
            -------------------------------------------------------------------- 
            local gwproxy, gwport, gwtransport = getgw(gateway)
            -- callerid type and privacy process
            local cidtype, _ = callerIdPrivacyProcess(route, InLeg)
            if cidtype~='none' then
                InLeg:execute("export", "nolocal:sip_from_display="..InLeg:getVariable("sip_from_display"))
                InLeg:execute("export", "nolocal:sip_invite_from_uri=<sip:"..InLeg:getVariable("sip_from_user").."@"..freeswitch.getGlobalVariable(sipprofile..':advertising')..">" )
                InLeg:execute("export", "nolocal:sip_invite_to_uri=<sip:"..InLeg:getVariable("sip_to_user").."@"..gwproxy..":"..gwport..";transport="..gwtransport..">")
            end
            -- media negotiation
            InLeg:execute("export", "media_mix_inbound_outbound_codecs=true")
            local outcodecstr = get_codec(route, OUTBOUND)
            InLeg:execute("export", "nolocal:absolute_codec_string="..outcodecstr)
            if gwtransport:lower() == 'tls' then
                InLeg:execute("export", "nolocal:rtp_secure_media=mandatory:"..ENCRYPTION_SUITES)
                InLeg:execute("export", "nolocal:sdp_secure_savp_only=true")
            end
            -- setting up vars
            InLeg:execute("export", "nolocal:origination_caller_id_name=".._clidname)
            InLeg:execute("export", "nolocal:origination_caller_id_number=".._clidnum)
            InLeg:execute("export", "nolocal:originate_timeout=90")
            InLeg:execute("export", "nolocal:fax_enable_t38=true")
            InLeg:execute("export", "nolocal:hangup_after_bridge=true")
            InLeg:execute("export", "nolocal:origination_uuid=".._uuid)
            InLeg:execute("export", "nolocal:X-LIBRE-ORIGIN-HOP="..intconname)
            InLeg:execute("export", "nolocal:X-LIBRE-INTCONNAME="..route)
            InLeg:setVariable("X-LIBRE-NEXT-HOP", route)

            -- outbound manipulation
            manipulate(name, DxLeg, NgVars)

            -- start outbound leg
            logify('module', 'callng', 'space', 'main', 'action', 'connect_gateway' , 'seshid', seshid, 'uuid', _uuid, 'route', route, 'sipprofile', sipprofile, 'gateway', gateway, 'forceroute', forceroute)
            OutLeg = freeswitch.Session("sofia/gateway/"..gateway.."/".._dnisnum, InLeg)

            -- check leg status
            local dialstatus = OutLeg:hangupCause()
            logify('module', 'callng', 'space', 'main', 'action', 'verify_state' , 'seshid', seshid, 'uuid', _uuid, 'attempt', attempt, 'status', dialstatus)

            if (ismeberof({'SUCCESS', 'NO_ANSWER', 'USER_BUSY', 'NORMAL_CLEARING', 'ORIGINATOR_CANCEL'}, dialstatus)) then break end
            ::ENDFAILOVER::
        end

        -- sleep to make sure channel available
        InLeg:sleep(500)

        if OutLeg then 
            if( OutLeg:ready() ) then
                -- log information for leg B
                local _real_uuid = OutLeg:get_uuid()
                if _uuid ~= _real_uuid then
                    logify('module', 'callng', 'space', 'main', 'seshid', seshid, 'action', 'report', 'pseudo_uuid', _uuid, 'native_uuid', _real_uuid)
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

                logify('module', 'callng', 'space', 'main', 'seshid', seshid, 'action', 'report', 'uuid', _real_uuid,
                       'context', _context, 'direction', _direction, 'sipprofile', _sofia_profile_name, 'ruri', _sip_req_uri, 'from_user', _sip_from_user, 
                       'to_user', _sip_to_user, 'destination_number', _destination_number, 'remote_ip', _sip_network_ip, 'callid', _sip_call_id)

                --- BRIDGE 2 LEGs
                logify('module', 'callng', 'space', 'main', 'seshid', seshid, 'action', 'bridge' , 'inbound_uuid', uuid, 'outbound_uuid', _real_uuid)
                freeswitch.bridge(InLeg, OutLeg)

                -- HANGUP WHEN DONE FOR OUTLEG
                if (OutLeg:ready()) then 
                    OutLeg:hangup(); 
                end
            else
                logify('module', 'callng', 'space', 'main', 'seshid', seshid, 'action', 'report', 'info', 'outbound.leg.not.connected')
            end
        end
        -----------------------------------------------------------
        --- HANGUP ONCE DONE
        -----------------------------------------------------------
        if (InLeg:ready()) then 
            logify('module', 'callng', 'space', 'main', 'action', 'endcall', 'seshid', seshid, 'traffic', 'ingress')
            InLeg:setVariable("X-LIBRE-HANGUP-CAUSE", LIBRE_HANGUP_CAUSE)
            InLeg:hangup(HANGUP_CAUSE); 
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
            InLeg:hangup(HANGUP_CAUSE) 
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
    logger("module=callng, space=main,  action=exception, error="..tostring(error))
end
---- close log ----
syslog.closelog()
