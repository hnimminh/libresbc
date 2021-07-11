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

require("callng.utilities")

-- global variables corresponding to defined values (e.g., flags) in kamailio.cfg
FLT_NATS=5
FLB_NATB=6
FLB_NATSIPPING=7

-- SIP request routing
-- equivalent of request_route{}
function ksr_request_route()
	-- debug log test
	delogify('module', 'callng', 'space', 'kami', 'action', 'new-request', 'ru', KSR.pv.get("$ru"))

	-- per request initial checks
	ksr_route_reqinit()

	-- NAT Detection and Fix
	ksr_route_natdetect()

	-- CANCEL processing
	if KSR.is_CANCEL() then
		ksr_route_relay()
		return 1
	end

	-- handle requests within SIP dialogs
	ksr_route_withindlg()

	if KSR.is_INVITE() then
		ksr_make_outcall()
		return 1
	end

	if KSR.corex.has_ruri_user() < 0 then
		-- request with no Username in RURI
		KSR.sl.sl_send_reply(484,"Address Incomplete")
		return 1
	end

	return 1
end


-- Per SIP request initial checks
function ksr_route_reqinit()
	-- rate limiting anti-flooding attached, optimize them later
	if not KSR.is_myself_srcip() then
		local srcip = KSR.kx.get_srcip();
		if KSR.htable.sht_match_name("ipban", "eq", srcip) > 0 then
			-- ip is already blocked
			delogify('module', 'callng', 'space', 'kami', 'action', 'blocked', 'method', KSR.kx.get_method(), 'fromuri', KSR.kx.get_furi(), 'srcip', srcip, 'srcport', KSR.kx.get_srcport())
			KSR.x.exit();
		end
		if KSR.pike.pike_check_req() < 0 then
			delogify('module', 'callng', 'space', 'kami', 'action', 'pike', 'method', KSR.kx.get_method(), 'fromuri', KSR.kx.get_furi(), 'srcip', srcip, 'srcport', KSR.kx.get_srcport())
			KSR.htable.sht_seti("ipban", srcip, 1);
			KSR.x.exit();
		end
	end

	-- blacked list user agent (hack, pentest, ddos)
	local ua = KSR.kx.gete_ua();
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

	if KSR.kx.get_msglen() > 4096 then
		KSR.sl.sl_send_reply(513,"Message Too Large")
		KSR.x.exit()
	end

	if KSR.maxfwd.process_maxfwd(10) < 0 then
		KSR.sl.sl_send_reply(483,"Too Many Hops")
		KSR.x.exit()
	end

	if KSR.sanity.sanity_check(1511, 7)<0 then
		delogify('module', 'callng', 'space', 'kami', 'action', 'malformed', 'srcip', srcip, 'srcport', KSR.kx.get_srcport())
		KSR.x.exit()
	end

	-- Do not support yet these method {MESSAGE, NOTIFY, PUBLISH, REFER, SUBSCRIBE}
	-- file the feature request if you wish them to be supported
    if KSR.is_method_in("MNPRS") then
		KSR.sl.sl_send_reply("405", "Method Not Allowed")
		KSR.x.exit()
	end

	-- Keepalive Repsonse
	if KSR.is_OPTIONS()
			and KSR.is_myself_ruri()
			and KSR.corex.has_ruri_user() < 0 then
		KSR.sl.sl_send_reply(200, "Keepalive")
		KSR.x.exit()
	end
end

-- Originator NAT Detection and Fix
function ksr_route_natdetect()
	KSR.force_rport();
	if KSR.nathelper.nat_uac_test(23)>0 then
		if KSR.is_REGISTER() then
			KSR.nathelper.fix_nated_register()
		elseif KSR.siputils.is_first_hop()>0 then
			KSR.nathelper.set_contact_alias()
		end
		KSR.setflag(FLT_NATS)
	end
	return 1
end


-- Handle requests within SIP dialogs
function ksr_route_withindlg()
	if KSR.siputils.has_totag()<0 then 
		return 1
	end

	if KSR.dialog.is_known_dlg()<0 then
		KSR.x.exit()
	end

	if KSR.rr.loose_route()>0 then
		KSR.hdr.append("P-hint: rr-enforced\r\n")
		ksr_route_relay()
		KSR.x.exit();
	end

	if KSR.is_ACK() then
		ksr_route_relay()
		KSR.x.exit()
	end
end

-- OUTCALL
function ksr_make_outcall()
	KSR.dialog.dlg_manage()
	KSR.rr.record_route()
	KSR.dispatcher.ds_select_dst(1)
	ksr_route_relay()
	KSR.x.exit()
end

-- RELAY
function ksr_route_relay()
	if KSR.tm.t_is_set("failure_route")<0 then
		KSR.tm.t_on_failure("ksr_failure_manage");
	end

	if KSR.is_CANCEL() then
		KSR.tm.t_relay_cancel()
	else
		KSR.tm.t_relay()
	end

	KSR.x.exit()
end

-- FAILURE MANAGE
function ksr_failure_manage()
	if KSR.tm.t_is_canceled()>0 then
		return 1
	end
	KSR.x.exit()
end
