--
-- callng:kami.lua
--
-- The Initial Developer of the Original Code is
-- Minh Minh <hnimminh at[@] outlook dot[.] com>
-- Portions created by the Initial Developer are Copyright (C) the Initial Developer.
-- All Rights Reserved.
-- ------------------------------------------------------------------------------------------------------------------------------------------------
--
-- KSR - the object exporting Kamailio KEMI functions (app_lua module)
-- sr - the old object exporting Kamailio functions (app_lua_sr module)
--
-- Relevant Remarks:
--  * do not execute Lua 'exit' - that will kill Lua interpreter which is embedded in Kamailio, resulting in killing Kamailio
--  * use KSR.x.exit() to trigger the stop of executing the script
--  * KSR.drop() is only marking the SIP message for drop, but doesn't stop the execution of the script. Use KSR.x.exit() after it or KSR.x.drop()
--
-- ------------------------------------------------------------------------------------------------------------------------------------------------
require("callng.sigfunc")
-- ------------------------------------------------------------------------------------------------------------------------------------------------
TRANSACTION_NATSCRIPT_FLAG = 5
BRANCH_NATOUT_FLAG = 6
BRANCH_NATSIPPING_FLAG = 7
SW_TRAFFIC_FLAG = 9
LIBRE_USER_LOCATION = 'LIBREUSRLOC'

-- ---------------------------------------------------------------------------------------------------------------------------------
--  MAIN  BLOCK - SIP REQUEST ROUTE
-- ---------------------------------------------------------------------------------------------------------------------------------
function ksr_request_route()
	delogify('module', 'callng', 'space', 'kami', 'action', 'request', 'method', KSR.kx.get_method(), 'ru', KSR.pv.get("$ru"), 'callid', KSR.kx.get_callid(), 'USRLOC', LIBRE_USER_LOCATION, 'LAYER', LAYER)

    sanitize()

	if KSR.is_OPTIONS() then
		keepalive()
	end

	srctraffic()
	nathandle()

	if KSR.is_CANCEL() then
		if KSR.tm.t_check_trans()>0 then
			ksr_route_relay()
		end
		return 1
	end

	withindlg()

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
		registrar()
	end

	-- incoming call
	if KSR.is_INVITE() then
		if KSR.isflagset(SW_TRAFFIC_FLAG) then
			call_from_switch()
		else
			call_from_public()
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
function sanitize()
	-- rate limiting anti-flooding attached, optimize them later
	if not KSR.is_myself_srcip() then
		local srcip = KSR.kx.get_srcip()
		if KSR.htable.sht_match_name("ipban", "eq", srcip) > 0 then
			-- ip is already blocked
			delogify('module', 'callng', 'space', 'kami', 'action', 'blocked', 'method', KSR.kx.get_method(), 'fromuri', KSR.kx.get_furi(), 'srcip', srcip, 'srcport', KSR.kx.get_srcport())
			KSR.x.exit()
		end
		if KSR.pike.pike_check_req() < 0 then
			delogify('module', 'callng', 'space', 'kami', 'action', 'pike', 'method', KSR.kx.get_method(), 'fromuri', KSR.kx.get_furi(), 'srcip', srcip, 'srcport', KSR.kx.get_srcport())
			KSR.htable.sht_seti("ipban", srcip, 1)
			KSR.x.exit()
		end
	end

	-- blacked list user agent (hack, pentest, ddos)
	local ua = KSR.kx.gete_ua()
	if string.find(ua, "friendly")
		or string.find(ua, "sipsak")
		or string.find(ua, "siparmyknife")
		or string.find(ua, "VaxIPUserAgent")
		or string.find(ua, "VaxSIPUserAgent")
		or string.find(ua, "scanner")
		or string.find(ua, "sipcli")
		or string.find(ua, "sipvicious") then
		KSR.drop()
		KSR.x.exit()
	end

	if KSR.kx.get_msglen()>4096 then
		KSR.sl.sl_send_reply(513,"Message Too Large")
		KSR.x.exit()
	end

	if KSR.maxfwd.process_maxfwd(10)<0 then
		KSR.sl.sl_send_reply(483,"Too Many Hops")
		KSR.x.exit()
	end

	if KSR.sanity.sanity_check(1511, 7)<0 then
		delogify('module', 'callng', 'space', 'kami', 'action', 'malformed', 'srcip', srcip, 'srcport', KSR.kx.get_srcport())
		KSR.x.exit()
	end

	-- Do not support yet these method {M:MESSAGE, N:NOTIFY, P:PUBLISH, F:REFER, S:SUBSCRIBE}
	-- file the feature request if you wish them to be supported
    if KSR.is_method_in("MNPFS") then
		KSR.sl.sl_send_reply("405", "Method Not Allowed")
		KSR.x.exit()
	end

end


-- ---------------------------------------------------------------------------------------------------------------------------------
--  DISTINCT AND TAG TRAFFIC
-- ---------------------------------------------------------------------------------------------------------------------------------
function srctraffic()
	local srcip = KSR.pv.get('$si')
	if ismeberof(B2BUA_LOOPBACK_IPADDRS, srcip) then
		KSR.setflag(SW_TRAFFIC_FLAG)
	end
end


-- ---------------------------------------------------------------------------------------------------------------------------------
-- NAT KEEPALIVE SIP OPTION
-- ---------------------------------------------------------------------------------------------------------------------------------
function keepalive()
	if KSR.is_myself_ruri() and KSR.corex.has_ruri_user()<0 then
		KSR.sl.sl_send_reply(200, "Keepalive")
		KSR.x.exit()
	end
end


-- ---------------------------------------------------------------------------------------------------------------------------------
-- NAT DETECT AND FIX|ALIAS
-- ---------------------------------------------------------------------------------------------------------------------------------
function nathandle()
	if KSR.isflagset(SW_TRAFFIC_FLAG) then
		return 1
	end
	KSR.force_rport()
	if KSR.nathelper.nat_uac_test(23)>0 then
		if KSR.is_REGISTER() then
			KSR.nathelper.fix_nated_register()
		elseif KSR.siputils.is_first_hop()>0 then
			KSR.nathelper.set_contact_alias()
		end
		KSR.setflag(TRANSACTION_NATSCRIPT_FLAG)
	end
	return 1
end


-- ---------------------------------------------------------------------------------------------------------------------------------
-- WRAP AROUND TM RELAY FUNCTION
-- enable additional event routes for forwarded requests
-- serial forking, RTP relaying handling, a.s.o.
-- ---------------------------------------------------------------------------------------------------------------------------------
function ksr_route_relay()
    if not KSR.isdsturiset() then
		KSR.nathelper.handle_ruri_alias()
	end
    -- local alias = KSR.nathelper.handle_ruri_alias()
	local relay = KSR.tm.t_relay()
	-- delogify('module', 'callng', 'space', 'kami', 'action', 'relay', 'state', relay, 'alias', alias)
	if relay<0 then
		KSR.sl.sl_reply_error()
	end
	KSR.x.exit()
end


-- ---------------------------------------------------------------------------------------------------------------------------------
-- WITHIN DIALOG SIP MESSAGE HANDLING
-- ---------------------------------------------------------------------------------------------------------------------------------
function withindlg()
	if KSR.siputils.has_totag()<0 then
		return 1
	end

	--[[
	if KSR.dialog.is_known_dlg()<0 then
		if KSR.is_ACK() and KSR.tm.t_check_trans()>0 then
			ksr_route_relay()
			KSR.x.exit()
		end
		KSR.x.exit()
	end
    ]]--

	-- sequential request withing a dialog should
	-- take the path determined by record-routing
	if KSR.rr.loose_route()>0 then
		ksr_route_relay()
		KSR.x.exit()
	end

	if KSR.is_ACK() then
		if KSR.tm.t_check_trans() >0 then
			-- no loose-route, but stateful ACK
			-- must be an ACK after a 487
			-- or e.g. 404 from upstream server
			ksr_route_relay()
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
    -- delogify('module', 'callng', 'space', 'kami', 'action', 'auth.report', 'domain', domain, 'authuser', authuser, 'callid', callid)
    if domain and authuser then
        local code, a1hash = authserect(domain, authuser)
        -- delogify('module', 'callng', 'space', 'kami', 'action', 'auth.report', 'domain', domain, 'authuser', authuser, 'callid', callid, 'code', code, 'a1hash', a1hash)
        if code == 1 then
            authcheck = KSR.auth.pv_auth_check(domain, a1hash, 1, 0)
            -- delogify('module', 'callng', 'space', 'kami', 'action', 'auth.check', 'domain', domain, 'authuser', authuser, 'callid', callid, 'authcheck', authcheck)
        end
    end
    if authcheck < 0 then
        KSR.auth.auth_challenge(domain, 0)
		-- delogify('module', 'callng', 'space', 'kami', 'action', 'auth.challenge')
		KSR.x.exit()
    else
        return authcheck, domain, authuser
    end
    -- delogify('module', 'callng', 'space', 'kami', 'action', 'auth.report', 'domain', domain, 'authuser', authuser, 'callid', callid, 'state', 'authorised')
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
function registrar()
    local _, domain, authuser = authenticate()

	if KSR.isflagset(TRANSACTION_NATSCRIPT_FLAG) then
		KSR.setbflag(BRANCH_NATOUT_FLAG)
		KSR.setbflag(BRANCH_NATSIPPING_FLAG)
	end

	local aorsaved = KSR.registrar.save_uri(LIBRE_USER_LOCATION, "5", "sip:"..authuser.."@"..domain)
	-- delogify('module', 'callng', 'space', 'kami', 'action', 'register.report', 'domain', domain, 'authuser', authuser, 'callid', callid, 'aorsaved', aorsaved)
	if aorsaved < 0 then
		KSR.sl.sl_reply_error()
	end

	KSR.auth.consume_credentials()
	KSR.x.exit()
end


-- ---------------------------------------------------------------------------------------------------------------------------------
-- PUBLIC CALL REQUEST
-- ---------------------------------------------------------------------------------------------------------------------------------
function call_from_public()
    local _, domain, authuser = authenticate()
	KSR.auth.consume_credentials()

    local dstsocket = DOMAIN_POLICIES[domain]['dstsocket']
    KSR.setdsturi('sip:'..dstsocket.ip..':'..dstsocket.port..';transport='..dstsocket.transport)
    local srcsocket = DOMAIN_POLICIES[domain]['srcsocket']
	KSR.pv.sets('$fs', srcsocket.transport.. ':'..srcsocket.ip..':'..srcsocket.port)
    -- KSR.dialog.dlg_manage()
	ksr_route_relay()
end


-- ---------------------------------------------------------------------------------------------------------------------------------
-- SW CALL REQUEST
-- ---------------------------------------------------------------------------------------------------------------------------------
function call_from_switch()
    local sipuser = KSR.hdr.get('X-USER-ID')
	local state = KSR.registrar.lookup_uri(LIBRE_USER_LOCATION, 'sip:'..sipuser)
	delogify('module', 'callng', 'space', 'kami', 'action', 'swcall.report', 'state', state, 'callid', KSR.kx.get_callid())
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
    -- KSR.dialog.dlg_manage()
	ksr_route_relay()
end


-- ---------------------------------------------------------------------------------------------------------------------------------
-- SIP RESPONSE HANDLING - REPLY ROUTE
-- ---------------------------------------------------------------------------------------------------------------------------------
function ksr_reply_route()
	-- delogify('module', 'callng', 'space', 'kami', 'action', 'route.reply')
    if not KSR.isflagset(SW_TRAFFIC_FLAG) then
        -- if KSR.isflagset(TRANSACTION_NATSCRIPT_FLAG) then
        if KSR.nathelper.nat_uac_test(23)>0 then
            if KSR.siputils.is_first_hop()>0 then
                KSR.nathelper.set_contact_alias()
            end
        end
    end
	return 1
end
