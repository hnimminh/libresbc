--
-- callng:main.lua
--
-- The Initial Developer of the Original Code is
-- Minh Minh <hnimminh at[@] outlook dot[.] com>
-- Portions created by the Initial Developer are Copyright (C) the Initial Developer.
-- All Rights Reserved.
--

require("callng.callfunc")
---------------------******************************---------------------
---------------------****|    CALLNG:MAIN     |****---------------------
---------------------******************************---------------------
local function main()
    local NgVars = {}
    local InLeg = session
    local OutLeg = nil
    NgVars.seshid = fsapi:execute('create_uuid')
    NgVars.ENCRYPTION_SUITES = table.concat(SRPT_ENCRYPTION_SUITES, ':')
    NgVars.LIBRE_HANGUP_CAUSE = 'NONE'
    local HANGUP_CAUSE = 'NORMAL_CLEARING'
    --- CALL PROCESSING
    if ( InLeg:ready() ) then
        -- get InLeg variables
        local uuid = InLeg:get_uuid()
        local context = InLeg:getVariable("context")
        local sipprofile = InLeg:getVariable("sofia_profile_name")
        local network_ip = InLeg:getVariable("sip_network_ip")
        NgVars.realm = InLeg:getVariable("domain_name")
        NgVars.intconname = InLeg:getVariable("user_name")
        local call_id = InLeg:getVariable("sip_call_id")
        local transport = InLeg:getVariable("sip_via_protocol")
        local caller_name = InLeg:getVariable("caller_id_name")
        local caller_number = InLeg:getVariable("caller_id_number")
        local destination_number = InLeg:getVariable("destination_number")
        -- log the incoming call request
        log.info('module=callng, space=main, action=inbound_call, seshid=%s, uuid=%s, context=%s, sipprofile=%s, network_ip=%s,'..
            'realm=%s, intconname=%s, call_id=%s, transport=%s, caller_name=%s, caller_number=%s, destination_number=%s',
            NgVars.seshid, uuid, context, sipprofile, network_ip, NgVars.realm, NgVars.intconname, call_id, transport, caller_name, caller_number, destination_number
        )
        -----------------------------------------------------------
        ---- IN LEG: INTIAL VAR
        -----------------------------------------------------------
        InLeg:execute("export", "X-LIBRE-SESHID="..NgVars.seshid)
        InLeg:setVariable("X-LIBRE-INTCONNAME", NgVars.intconname)
        -- call will be reject if inbound interconnection is not enable
        if not is_intcon_enable(NgVars.intconname, INBOUND) then
            log.info('module=callng, space=main, action=state_check, seshid=%s, uuid=%s, intconname=%s, state=disabled, donext=hangup_as_disabled', NgVars.seshid, uuid,  NgVars.intconname)
            HANGUP_CAUSE = 'CHANNEL_UNACCEPTABLE'; NgVars.LIBRE_HANGUP_CAUSE = 'DISABLED_CONNECTION'; goto ENDSESSION
        end

        -- call will be reject if inbound interconnection reach max capacity
        local concurentcalls, max_concurentcalls =  verify_concurentcalls(NgVars.intconname, INBOUND, uuid)
        log.info('module=callng, space=main, action=concurency_check, seshid=%s, uuid=%s, intconname=%s, concurentcalls=%s, max_concurentcalls=%s', NgVars.seshid, uuid, NgVars.intconname, concurentcalls, max_concurentcalls)
        if concurentcalls > max_concurentcalls then
            HANGUP_CAUSE = 'CALL_REJECTED'; NgVars.LIBRE_HANGUP_CAUSE = 'MAX_CONCURENT_CALL'; goto ENDSESSION
        end

        -- call will be blocked if inbound interconnection is violated the cps
        local is_passed, current_cps, max_cps, block_ms = verify_cps(NgVars.intconname, INBOUND, uuid)
        log.info('module=callng, space=main, action=cps_check, seshid=%s, uuid=%s, intconname=%s, result=%s, current_cps=%s, max_cps=%s, block_ms=%s', NgVars.seshid, uuid, NgVars.intconname, is_passed, current_cps, max_cps, block_ms)
        if not is_passed then
            HANGUP_CAUSE = 'CALL_REJECTED'; NgVars.LIBRE_HANGUP_CAUSE = 'MAX_CPS'; goto ENDSESSION
        end
        -- translation
        local tranrules
        NgVars.cidnumber, NgVars.cidname, NgVars.dstnumber, tranrules = translate(caller_number, caller_name, destination_number, NgVars.intconname, INBOUND)
        log.info('module=callng, space=main, action=translate, seshid=%s, uuid=%s, direction=%s, intconname=%s, tranrules=%s, cidnumber=%s, cidname=%s, dstnumber=%s',
            NgVars.seshid, uuid, INBOUND, NgVars.intconname, rulejoin(tranrules), NgVars.cidnumber, NgVars.cidname, NgVars.dstnumber)
        -- media negotiation - secure
        inMediaProcess(NgVars.intconname, InLeg)
        if transport:lower()=='tls' then
            InLeg:setVariable("rtp_secure_media", "mandatory:"..NgVars.ENCRYPTION_SUITES)
            InLeg:setVariable("sdp_secure_savp_only", "true")
        end
        --------------------------------------------------------------------
        -- inbound normalization
        normalize(InLeg, NgVars)
        --------------------------------------------------------------------

        -- routing
        local routingrules
        local routingname = InLeg:getVariable("x-routing-plan")
        NgVars.route1, NgVars.route2, routingrules = routing_query(routingname, NgVars)

        local routingrulestr = 'no.matching.route.found'
        if (#routingrules > 0) then routingrulestr = rulejoin(routingrules) end

        log.info('module=callng, space=main, action=routing_query, seshid=%s, uuid=%s, intconname=%s, routingname=%s, NgVars=%s, route1=%s, route2=%s, routingrules=%s',
                NgVars.seshid, uuid, NgVars.intconname, routingname,  json.encode(NgVars), NgVars.route1, NgVars.route2, routingrulestr)

        if not (NgVars.route1 and NgVars.route2) then
            HANGUP_CAUSE = 'NO_ROUTE_DESTINATION'; NgVars.LIBRE_HANGUP_CAUSE = 'ROUTE_NOT_FOUND'; goto ENDSESSION    -- SIP 404 NO_ROUTE_DESTINATION
        end

        -- blocking call checking
        if (NgVars.route1 == BLOCK) or (NgVars.route2 == BLOCK) then
            log.info('module=callng, space=main, action=hangup_as_block, seshid=%s, uuid=%s, intconname=%s', NgVars.seshid, uuid, NgVars.intconname)
            HANGUP_CAUSE = 'CALL_REJECTED'; NgVars.LIBRE_HANGUP_CAUSE = 'BLOCK_CALL'; goto ENDSESSION  -- SIP 603 Decline
        end
        --------------------------------------------------------------------
        if InLeg:getVariable("x-ringready") then InLeg:execute('ring_ready') end
        earlyMediaProcess(NgVars.intconname, InLeg)
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
        local routes = (NgVars.route1==NgVars.route2) and {NgVars.route1} or {NgVars.route1, NgVars.route2}
        for attempt=1, #routes do
            _uuid = fsapi:execute('create_uuid')
            NgVars.route = routes[attempt]

            -- if state is disable then try next route or drop call
            if not is_intcon_enable(NgVars.route, OUTBOUND) then
                log.info('module=callng, space=main, action=state_check, seshid=%s, uuid=%s, route=%s, state=disabled, donext=hangup_as_disabled', NgVars.seshid, _uuid, NgVars.route)
                if attempt >= #routes then HANGUP_CAUSE = 'CHANNEL_UNACCEPTABLE'; NgVars.LIBRE_HANGUP_CAUSE = 'DISABLED_CONNECTION' end; goto ENDFAILOVER
            end

            -- call will be reject if outbound interconnection reach max capacity
            local _concurentcalls, _max_concurentcalls =  verify_concurentcalls(NgVars.route, OUTBOUND, _uuid)
            log.info('module=callng, space=main, action=concurency_check, seshid=%s, uuid=%s, route=%s, concurentcalls=%s, max_concurentcalls=%s', NgVars.seshid, _uuid, NgVars.route, _concurentcalls, _max_concurentcalls)
            if _concurentcalls >= _max_concurentcalls then
                if attempt >= #routes then HANGUP_CAUSE = 'CALL_REJECTED'; NgVars.LIBRE_HANGUP_CAUSE = 'MAX_CONCURENT_CALL' end; goto ENDFAILOVER
            end

            -- call will be reject if outbound interconnection reach max cps
            local waitms, queue, max_cps = average_cps(NgVars.route, OUTBOUND)
            log.info('module=callng, space=main, action=average_cps, seshid=%s, uuid=%s, route=%s, waitms=%s, queue=%s, max_cps=%s', NgVars.seshid, _uuid, NgVars.route, waitms, queue, max_cps)
            if queue >  max_cps then
                HANGUP_CAUSE = 'CALL_REJECTED'; NgVars.LIBRE_HANGUP_CAUSE = 'MAX_QUEUE'; goto ENDFAILOVER
            else InLeg:sleep(waitms) end

            -- translation
            local _tranrules
            NgVars._cidnumber, NgVars._cidname, NgVars._dstnumber, _tranrules = translate(NgVars.cidnumber, NgVars.cidname, NgVars.dstnumber, NgVars.route, OUTBOUND)
            log.info('module=callng, space=main, action=translate, seshid=%s, uuid=%s, direction=%s, route=%s, tranrules=%s, cidnumber=%s, cidname=%s, dstnumber=%s',
                    NgVars.seshid, _uuid, OUTBOUND, NgVars.route, rulejoin(_tranrules), NgVars._cidnumber, NgVars._cidname, NgVars._dstnumber)

            -- distributes calls to gateways in a weighted base
            local forceroute = false
            local _sipprofile = get_sipprofile(NgVars.route, OUTBOUND)
            local dpalgorithm = get_distribution_algorithm(NgVars.route)

            local gateway = '-err'
            if dpalgorithm == 'hash_callid' then gateway = hashchoicegw(NgVars.route, _sipprofile, call_id)
            elseif dpalgorithm == 'hash_src_ip' then gateway = hashchoicegw(NgVars.route, _sipprofile, network_ip)
            elseif dpalgorithm == 'hash_destination_number' then gateway = hashchoicegw(NgVars.route, _sipprofile, destination_number)
            else
                gateway = fsapi:execute('expand', 'distributor '..NgVars.route..' ${sofia profile '.._sipprofile..' gwlist down}')
            end
            if gateway == '-err' then
                gateway = fsapi:execute('distributor', NgVars.route)
                forceroute = true
            end
            --------------------------------------------------------------------
            local gwproxy, gwport, gwtransport = getgw(gateway)
            -- callerid type and privacy process
            local cidtype, _ = callerIdPrivacyProcess(NgVars.route, InLeg)
            if cidtype~='none' then
                local sipadip = freeswitch.getGlobalVariable(_sipprofile..':advertising')
                if not sipadip then sipadip = freeswitch.getGlobalVariable('hostname') end
                local sip_from_display = InLeg:getVariable("sip_from_display")
                if sip_from_display then InLeg:execute("export", "nolocal:sip_from_display="..sip_from_display) end
                local sip_from_user = InLeg:getVariable("sip_from_user")
                if sip_from_user then InLeg:execute("export", "nolocal:sip_invite_from_uri=<sip:"..sip_from_user.."@"..sipadip..">") end
                local sip_to_user = InLeg:getVariable("sip_to_user")
                if sip_to_user then InLeg:execute("export", "nolocal:sip_invite_to_uri=<sip:"..sip_to_user.."@"..gwproxy..":"..gwport..";transport="..gwtransport..">") end
            end
            -- media negotiation - secure
            InLeg:execute("export", "media_mix_inbound_outbound_codecs=true")
            outMediaProcess(NgVars.route, InLeg)
            if gwtransport:lower() == 'tls' then
                InLeg:execute("export", "nolocal:rtp_secure_media=mandatory:"..NgVars.ENCRYPTION_SUITES)
                InLeg:execute("export", "nolocal:sdp_secure_savp_only=true")
            end

            -- setting up vars
            InLeg:execute("export", "nolocal:origination_caller_id_name="..NgVars._cidname)
            InLeg:execute("export", "nolocal:origination_caller_id_number="..NgVars._cidnumber)
            InLeg:execute("export", "nolocal:originate_timeout=90")
            InLeg:execute("export", "nolocal:fax_enable_t38=true")
            InLeg:execute("export", "nolocal:hangup_after_bridge=true")
            InLeg:execute("export", "nolocal:origination_uuid=".._uuid)
            InLeg:execute("export", "nolocal:X-LIBRE-ORIGIN-HOP="..NgVars.intconname)
            InLeg:execute("export", "nolocal:X-LIBRE-INTCONNAME="..NgVars.route)
            InLeg:setVariable("X-LIBRE-NEXT-HOP", NgVars.route)

            --------------------------------------------------------------------
            -- outbound manipulation
            manipulate(InLeg, NgVars)
            --------------------------------------------------------------------

            -- start outbound leg
            log.info('module=callng, space=main, action=connect_gateway, seshid=%s, uuid=%s, route=%s, sipprofile=%s, gateway=%s, algorithm=%s, forceroute=%s',
                    NgVars.seshid, _uuid, NgVars.route, _sipprofile, gateway, algorithm, forceroute)
            OutLeg = freeswitch.Session("sofia/gateway/"..gateway.."/"..NgVars._dstnumber, InLeg)

            -- check leg status
            local dialstatus = OutLeg:hangupCause()
            log.info('module=callng, space=main, action=verify_state, seshid=%s, uuid=%s, attempt=%s, gateway=%s, status=%s', NgVars.seshid, _uuid, attempt, gateway, dialstatus)

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
                    log.warning('module=callng, space=main, action=faultdetect, seshid=%s, pseudo_uuid=%s, native_uuid=%s', NgVars.seshid, _uuid, _real_uuid)
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
                log.info('module=callng, space=main, action=report, seshid=%s, uuid=%s, context=%s, direction=%s, sipprofile=%s, ruri=%s, from_user=%s, to_user=%s, destination_number=%s, remote_ip=%s, callid=%s',
                    NgVars.seshid, _real_uuid, _context, _direction, _sofia_profile_name, _sip_req_uri, _sip_from_user, _sip_to_user, _destination_number, _sip_network_ip, _sip_call_id)

                --- BRIDGE 2 LEGs
                log.info('module=callng, space=main, action=bridge, seshid=%s, inbound_uuid=%s, outbound_uuid=%s', NgVars.seshid, uuid, _real_uuid)
                freeswitch.bridge(InLeg, OutLeg)

                -- HANGUP WHEN DONE FOR OUTLEG
                if (OutLeg:ready()) then
                    OutLeg:hangup()
                end
            else
                log.warning('module=callng, space=main, action=callstate, seshid=%s, info=outbound.leg.not.connected', NgVars.seshid)
            end
        end
        -----------------------------------------------------------
        --- HANGUP ONCE DONE
        -----------------------------------------------------------
        if (InLeg:ready()) then
            log.info('module=callng, space=main, action=endcall, seshid=%s, status=done', NgVars.seshid)
            InLeg:setVariable("X-LIBRE-HANGUP-CAUSE", NgVars.LIBRE_HANGUP_CAUSE)
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
            InLeg:setVariable("X-LIBRE-HANGUP-CAUSE", NgVars.LIBRE_HANGUP_CAUSE)
            InLeg:hangup(HANGUP_CAUSE)
        end
    end
    if OutLeg then
        if (OutLeg:ready()) then
            OutLeg:setVariable("X-LIBRE-HANGUP-CAUSE", NgVars.LIBRE_HANGUP_CAUSE)
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
    log.critical('module=callng, space=main, action=exception, error=%s', error)
end
---- close log ----
syslog.closelog()
