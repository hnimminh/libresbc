--
-- callng:kami.lua
--
-- The Initial Developer of the Original Code is
-- Minh Minh <hnimminh at[@] outlook dot[.] com>
-- Portions created by the Initial Developer are Copyright (C) the Initial Developer.
-- All Rights Reserved.
--
-- ------------------------------------------------------------------------------------------------------------------------------------------------
require("callng.sigfunc")
-- ------------------------------------------------------------------------------------------------------------------------------------------------
TRANSACTION_NAT_SCRIPT_FLAG = 5
SELFSW_TRAFFIC_SCRIPT_FLAG = 9
-- ---------------------------------------------------------------------------------------------------------------------------------
--  MAIN BLOCK - SIP REQUEST ROUTE
-- ---------------------------------------------------------------------------------------------------------------------------------
function ksr_request_route()
    --  DISTINCT AND TAG TRAFFIC
    if ismeberof(SELFSW_IPADDRS, KSR.pv.get('$si')) then
        KSR.setflag(SELFSW_TRAFFIC_SCRIPT_FLAG)
    end
    -- CHECK
    SecurityCheck()

    --  NAT KEEPALIVE SIP OPTION
	if KSR.is_OPTIONS() then
        if KSR.is_myself_ruri() and KSR.corex.has_ruri_user()<0 then
            KSR.sl.sl_send_reply(200, "Keepalive")
            KSR.x.exit()
        end
	end
    -- NAT
	NatHandle()

    -- CANCEL
	if KSR.is_CANCEL() then
		if KSR.tm.t_check_trans()>0 then
			RouteRelay()
		end
		return 1
	end

    -- IN DIALOG
	WithinDialogProcess()

	-- only initial requests (no To tag), handle retransmissions
	if KSR.tmx.t_precheck_trans()>0 then
		KSR.tm.t_check_trans()
		return 1
	end
	if KSR.tm.t_check_trans()==0 then
		return 1
	end

	-- record routing for dialog forming requests (in case they are routed)
	-- remove preloaded route headers
	KSR.hdr.remove("Route")
	if KSR.is_method_in("IS") then
		KSR.rr.record_route()
	end

	-- registrar service with user authentication
	if KSR.is_REGISTER() then
		RegistrarService()
	end

	-- incoming call
	if KSR.is_INVITE() then
		if KSR.isflagset(SELFSW_TRAFFIC_SCRIPT_FLAG) then
			SwitchThenProxy()
		else
			ProxyThenSwitch()
		end
	end

	if KSR.corex.has_ruri_user() < 0 then
		-- request with no Username in RURI
		KSR.sl.sl_send_reply(484,"Address Incomplete")
		return 1
	end

	return 1
end


-- ---------------------------------------------------------------------------------------------------------------------------------
--  INITIAL SANITY SECURITY CHECK & POLICY
-- ---------------------------------------------------------------------------------------------------------------------------------
function SecurityCheck()
    local srcip = KSR.kx.get_srcip()
    local useragent = KSR.kx.get_ua()
    -- RATE SECURITY
	if not KSR.is_myself_srcip() and not KSR.isflagset(SELFSW_TRAFFIC_SCRIPT_FLAG) then
        if KSR.pike then
            -- ANTI FLOODING
            local floodcount = KSR.htable.sht_get("antiflooding", srcip)
            if floodcount then
                if floodcount >= AUTIFLOODING_THRESHOLD and AUTIFLOODING_THRESHOLD > 0 then
                    secpublish('antiflooding', srcip, AUTIFLOODING_BANTIME, LAYER, useragent, nil, floodcount)
                end
                KSR.x.exit()
            end
            if KSR.pike.pike_check_req() < 0 then
                delogify('module', 'callng', 'space', 'kami', 'layer', LAYER, 'action', 'sanity.flooding.detected', 'srcip', srcip, 'useragent', useragent)
                if not floodcount then
                    KSR.htable.sht_seti("antiflooding", srcip, 1)
                end
                KSR.x.exit()
            end
        end
        local failcount = KSR.htable.sht_get("authfailure", srcip)
        if failcount and failcount >= AUTHFAILURE_THRESHOLD then
            if failcount <= AUTHFAILURE_THRESHOLD+3 then
                delogify('module', 'callng', 'space', 'kami', 'layer', LAYER, 'action', 'sanity.auth.banned', 'srcip', srcip, 'useragent', useragent, 'failcount', failcount)
                KSR.htable.sht_inc("authfailure", srcip)
            end
			KSR.x.exit()
		end
	end
	-- UA BLACKLIST
    local ua = KSR.kx.gete_ua()
    if string.find(ua, "friendly")
		or string.find(ua, "sipsak")
		or string.find(ua, "siparmyknife")
		or string.find(ua, "VaxIPUserAgent")
		or string.find(ua, "VaxSIPUserAgent")
		or string.find(ua, "scanner")
		or string.find(ua, "sipcli")
        or string.find(ua, "test")
		or string.find(ua, "sipvicious") then
		KSR.x.exit()
	end
    -- SANITY TEST
	if KSR.kx.get_msglen()>4096 then
		KSR.sl.sl_send_reply(513,"Message Too Large")
		KSR.x.exit()
	end
	if KSR.maxfwd.process_maxfwd(10)<0 then
		KSR.sl.sl_send_reply(483,"Too Many Hops")
		KSR.x.exit()
	end
	if KSR.sanity.sanity_check(17895, 7)<0 then
		delogify('module', 'callng', 'space', 'kami', 'layer', LAYER, 'action', 'malformed', 'srcip', srcip, 'useragent', useragent)
		KSR.x.exit()
	end
    -- CVE-2018-8828 [Fixed Already]
    local ruser = KSR.kx.get_ruser()
    if ruser and #ruser > 32 then
        KSR.sl.sl_send_reply(488, "Not Acceptable Here")
        KSR.x.exit()
    end
    -- SPOOFING DECTION
    if KSR.hdr.is_present('Record-Route')>0 then
        if string.find(KSR.hdr.get_idx('Record-Route', 0), srcip) then
            KSR.sl.sl_send_reply(488, "Not Acceptable Here")
            KSR.x.exit()
        end
    end
	-- Do not support yet these method {M:MESSAGE, N:NOTIFY, P:PUBLISH, F:REFER, S:SUBSCRIBE}
	-- file the feature request if you wish them to be supported
    if KSR.is_method_in("MNPFS") then
		KSR.sl.sl_send_reply(405, "Method Not Allowed")
		KSR.x.exit()
	end
end

-- ---------------------------------------------------------------------------------------------------------------------------------
-- NAT DETECT AND FIX|ALIAS
-- ---------------------------------------------------------------------------------------------------------------------------------
function NatHandle()
	if KSR.isflagset(SELFSW_TRAFFIC_SCRIPT_FLAG) then
		return 1
	end
	KSR.force_rport()
	if KSR.nathelper.nat_uac_test(23)>0 then
		if KSR.is_REGISTER() then
			KSR.nathelper.fix_nated_register()
		elseif KSR.siputils.is_first_hop()>0 then
			KSR.nathelper.set_contact_alias()
		end
		KSR.setflag(TRANSACTION_NAT_SCRIPT_FLAG)
	end
	return 1
end


-- ---------------------------------------------------------------------------------------------------------------------------------
-- WRAP AROUND TM RELAY FUNCTION
-- enable additional event routes for forwarded requests
-- serial forking, RTP relaying handling, a.s.o.
-- ---------------------------------------------------------------------------------------------------------------------------------
function RouteRelay()
    if not KSR.isdsturiset() then
		KSR.nathelper.handle_ruri_alias()
	end
    -- local alias = KSR.nathelper.handle_ruri_alias()
	local relay = KSR.tm.t_relay()
	-- delogify('module', 'callng', 'space', 'kami', 'layer', LAYER, 'action', 'relay', 'state', relay, 'alias', alias)
	if relay<0 then
		KSR.sl.sl_reply_error()
	end
	KSR.x.exit()
end


-- ---------------------------------------------------------------------------------------------------------------------------------
-- WITHIN DIALOG SIP MESSAGE HANDLING
-- ---------------------------------------------------------------------------------------------------------------------------------
function WithinDialogProcess()
	if KSR.siputils.has_totag()<0 then
		return 1
	end

	-- sequential request withing a dialog should
	-- take the path determined by record-routing
	if KSR.rr.loose_route()>0 then
		RouteRelay()
		KSR.x.exit()
	end

	if KSR.is_ACK() then
		if KSR.tm.t_check_trans() >0 then
			-- no loose-route, but stateful ACK
			-- must be an ACK after a 487
			-- or e.g. 404 from upstream server
			RouteRelay()
			KSR.x.exit()
		else
			-- ACK without matching transaction ... ignore and discard
			KSR.x.exit()
		end
	end
	KSR.sl.sl_send_reply(404, "Not Here")
	KSR.x.exit()
end

-- ---------------------------------------------------------------------------------------------------------------------------------
-- DIGEST AUTHENTICATE
-- ---------------------------------------------------------------------------------------------------------------------------------
function authenticate()
    local domain = KSR.kx.get_fhost()
    local authuser = KSR.kx.get_au()
    local callid = KSR.kx.get_callid()
    local authcheck = -9
    -- delogify('module', 'callng', 'space', 'kami', 'layer', LAYER, 'action', 'auth.report', 'domain', domain, 'authuser', authuser, 'callid', callid)
    if domain and authuser then
        local code, a1hash = authserect(domain, authuser)
        -- delogify('module', 'callng', 'space', 'kami', 'layer', LAYER, 'action', 'auth.report', 'domain', domain, 'authuser', authuser, 'callid', callid, 'code', code, 'a1hash', a1hash)
        if code == 1 then
            authcheck = KSR.auth.pv_auth_check(domain, a1hash, 21, 0)
            -- delogify('module', 'callng', 'space', 'kami', 'layer', LAYER, 'action', 'auth.check', 'domain', domain, 'authuser', authuser, 'callid', callid, 'authcheck', authcheck)
        end
        -- BRUTEFORCE & INTRUSION PREVENTION
        if code <= 0 or authcheck <= 0 then
            local srcip = KSR.kx.get_srcip()
            local failcount = KSR.htable.sht_inc("authfailure", srcip)
            if failcount <= 0 then
                KSR.htable.sht_seti("authfailure", srcip, 1)
                failcount = 1
            end
            if failcount >= AUTHFAILURE_THRESHOLD then
                local useragent = KSR.kx.get_ua()
                local attackcount = KSR.htable.sht_inc("attackavoid", srcip)
                if attackcount <= 0 then
                    KSR.htable.sht_seti("attackavoid", srcip, 1)
                    attackcount = 1
                end
                if attackcount >= ATTACKAVOID_THRESHOLD then
                    secpublish('attackavoid', srcip, ATTACKAVOID_BANTIME, LAYER, useragent, authuser, attackcount)
                else secpublish('authfailure', srcip, AUTHFAILURE_BANTIME, LAYER, useragent, authuser, failcount) end
            end
        end
    end
    if authcheck < 0 then
        KSR.auth.auth_challenge(domain, 21)
		KSR.x.exit()
    else
        return authcheck, domain, authuser
    end
    -- delogify('module', 'callng', 'space', 'kami', 'layer', LAYER, 'action', 'auth.report', 'domain', domain, 'authuser', authuser, 'callid', callid, 'state', 'authorised')
end

-- ---------------------------------------------------------------------------------------------------------------------------------
-- IP AUTHENTICATE
-- ---------------------------------------------------------------------------------------------------------------------------------
function iptrust()
    local domain = KSR.kx.get_fhost()
    local srcip = KSR.kx.get_srcip()
    local callid = KSR.kx.get_callid()
end

-- ---------------------------------------------------------------------------------------------------------------------------------
-- REGISTRAR SERVICE
-- ---------------------------------------------------------------------------------------------------------------------------------
function RegistrarService()
    local _, domain, authuser = authenticate()

	if KSR.isflagset(TRANSACTION_NAT_SCRIPT_FLAG) then
		KSR.setbflag(BRANCH_NATOUT_FLAG)
		KSR.setbflag(BRANCH_NATSIPPING_FLAG)
	end

	local aorsaved = KSR.registrar.save_uri(LIBRE_USER_LOCATION, "5", "sip:"..authuser.."@"..domain)
	-- delogify('module', 'callng', 'space', 'kami', 'layer', LAYER, 'action', 'register.report', 'domain', domain, 'authuser', authuser, 'aorsaved', aorsaved)
	if aorsaved < 0 then
		KSR.sl.sl_reply_error()
	end

	KSR.auth.consume_credentials()
	KSR.x.exit()
end


-- ---------------------------------------------------------------------------------------------------------------------------------
-- PROXY GOTO SWITCH
-- ---------------------------------------------------------------------------------------------------------------------------------
function ProxyThenSwitch()
    local _, domain, authuser = authenticate()
	KSR.auth.consume_credentials()
    delogify('module', 'callng', 'space', 'kami', 'layer', LAYER, 'action', 'uacincoming', 'domain', domain, 'authuser', authuser, 'callid', KSR.kx.get_callid())
    local dstsocket = DOMAIN_POLICIES[domain]['dstsocket']
    KSR.setdsturi('sip:'..dstsocket.ip..':'..dstsocket.port..';transport='..dstsocket.transport)
    local srcsocket = DOMAIN_POLICIES[domain]['srcsocket']
	KSR.pv.sets('$fs', srcsocket.transport.. ':'..srcsocket.ip..':'..srcsocket.port)

    -- APPEND X-HEADER
    KSR.hdr.append('X-ACCESS-AUTHID: '..authuser..'@'..domain..'\r\n')
    KSR.hdr.append('X-ACCESS-SRCIP: '..KSR.kx.get_srcip()..'\r\n')

    -- KSR.dialog.dlg_manage()
	RouteRelay()
end


-- ---------------------------------------------------------------------------------------------------------------------------------
-- SWITCH GOTO PROXY
-- ---------------------------------------------------------------------------------------------------------------------------------
function SwitchThenProxy()
    local sipuser = KSR.hdr.get('X-ACCESS-USERID')
	local state = KSR.registrar.lookup_uri(LIBRE_USER_LOCATION, 'sip:'..sipuser)
    delogify('module', 'callng', 'space', 'kami', 'layer', LAYER, 'action', 'uasoutgoing', 'state', state, 'sipuser', sipuser, 'callid', KSR.kx.get_callid())
	if state<0 then
		KSR.tm.t_newtran()
		if state==-1 or state==-3 then
			KSR.sl.send_reply(404, "Not Found")
			KSR.x.exit()
		elseif state==-2 then
			KSR.sl.send_reply(405, "Method Not Allowed")
			KSR.x.exit()
		end
	end

    -- REMOVE X-HEADER
    KSR.hdr.remove('X-ACCESS-USERID')

    -- KSR.dialog.dlg_manage()
	RouteRelay()
end


-- ---------------------------------------------------------------------------------------------------------------------------------
-- SIP RESPONSE HANDLING - REPLY ROUTE
-- ---------------------------------------------------------------------------------------------------------------------------------
function ksr_reply_route()
    if not KSR.isflagset(SELFSW_TRAFFIC_SCRIPT_FLAG) then
        if KSR.nathelper.nat_uac_test(23)>0 then
            if KSR.siputils.is_first_hop()>0 then
                KSR.nathelper.set_contact_alias()
            end
        end
    end
	return 1
end
