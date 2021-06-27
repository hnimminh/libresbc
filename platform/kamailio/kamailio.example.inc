#!KAMAILIO

# Defined Values
# ==============

# #!define WITH_DEBUG 1

## To be activated for SBC and AIO roles
#!define WITH_ANTIFLOOD 1
##

#!define SCANNER_BLACKLIST "sipsak|friendly-scanner|sipvicious|sipcli|sip-scan|sundayddr|iWar|CSipSimple|SIVuS|Gulp|sipv|smap|friendly-request|VaxIPUserAgent|VaxSIPUserAgent|siparmyknife|Test Agent"

# #!define WITH_DMQ 1

## To be activated for SIP Router and AIO roles
#!define WITH_AUTH 1
#!define WITH_UAC_REG 1
##

#!define FLT_ACC 1
#!define FLT_ACCMISSED 2
#!define FLT_ACCFAILED 3
#!define FLT_NATS 5

#!define FLB_NATB 6
#!define FLB_NATSIPPING 7


# Global Parameters
# =================

children=8

log_facility=LOG_LOCAL0
log_prefix="{$mt $hdr(CSeq) $ci} "

memdbg=5
memlog=5

tcp_accept_no_cl=yes

# LOG Levels: 3=DBG, 2=INFO, 1=NOTICE, 0=WARN, -1=ERR
#!ifdef WITH_DEBUG
debug=4
log_stderror=yes
sip_warning=1
#!else
debug=2
log_stderror=no
sip_warning=0
#!endif


# Local config file (if it exists)
# ================================
### import_file "local.cfg"

# *** Value defines - IDs used later in config

/* API endpoints */
# #!define HTTP_API_ROUTING_ENDPOINT "http://librekam-router-confd:9600/1.0/kamailio/routing"
# #!define HTTP_API_CDR_ENDPOINT "http://librekam-router-confd:9600/1.0/kamailio/cdr"
# #!define HTTP_API_DBTEXT_UACREG_ENDPOINT "http://librekam-router-confd:9600/1.0/kamailio/dbtext/uacreg"

/* set the auth SECRET, defaults to randomly generated string */
# #!define ROUTER_AUTH_SECRET "librekam"

/* set the list of RTPengine instances */
# #!define RTPENGINE_LIST "udp:localhost:22222"

/* add API http timeout */
# #!define HTTP_API_TIMEOUT 5000

/* add listen protocol, address and port / advertise (optional) */
# #!define LISTEN udp:192.168.1.1:5060 advertise c4.librekam.community
# #!define LISTEN_XHTTP tcp:lo:9601

/* Address to be used to build contact address when registering to carriers */
# #!define REG_CONTACT_ADDRESS localhost:5060

/* Directory to store dbtext tables */
# #!define DBTEXT_DIRECTORY "/etc/kamailio/dbtext"

/* DB url for UAC registration */
# #!define REG_DB_URL "text:///etc/kamailio/dbtext"

/* DB url for domain module */
# #!define DOMAIN_DB_URL "text:///etc/kamailio/dbtext"



# Default Values
# ==============

#!ifndef DBTEXT_DIRECTORY
#!define DBTEXT_DIRECTORY "/etc/kamailio/dbtext"
#!endif

#!ifndef REG_DB_URL
#!define REG_DB_URL "text:///etc/kamailio/dbtext"
#!endif

#!ifndef DOMAIN_DB_URL
#!define DOMAIN_DB_URL "text:///etc/kamailio/dbtext"
#!endif

#!ifndef DBURL_DIALOG
#!define DBURL_DIALOG "redis://redis:6379/7"
#!endif

#!ifndef LISTEN_XHTTP
#!define LISTEN_XHTTP tcp:eth0:9601
#!endif

#!ifndef REG_CONTACT_ADDRESS
#!define REG_CONTACT_ADDRESS "localhost:5060"
#!endif

#!ifndef HTTP_ASYNC_CLIENT_WORKERS
#!define HTTP_ASYNC_CLIENT_WORKERS 8
#!endif

#!ifdef LISTEN_ADVERTISE
listen=LISTEN advertise LISTEN_ADVERTISE
#!else
listen=LISTEN
#!endif
listen=LISTEN_XHTTP
#!ifdef WITH_DMQ
listen=DMQ_LISTEN
#!endif

#!ifdef ALIAS
alias=ALIAS
#!endif


# Modules Section
# ===============

loadmodule "jsonrpcs.so"
loadmodule "kex.so"
loadmodule "corex.so"
loadmodule "tm.so"
loadmodule "tmx.so"
loadmodule "sl.so"
loadmodule "rr.so"
loadmodule "pv.so"
loadmodule "maxfwd.so"
loadmodule "usrloc.so"
loadmodule "registrar.so"
loadmodule "textops.so"
loadmodule "sdpops.so"
loadmodule "siputils.so"
loadmodule "xlog.so"
loadmodule "sanity.so"
loadmodule "ctl.so"
loadmodule "cfg_rpc.so"
loadmodule "acc.so"
loadmodule "counters.so"
loadmodule "http_async_client.so"
loadmodule "rtjson.so"
loadmodule "jansson.so"
loadmodule "nathelper.so"
loadmodule "db_text.so"
loadmodule "db_redis.so"
loadmodule "xhttp.so"
loadmodule "uac.so"
loadmodule "exec.so"

loadmodule "rtpengine.so"
loadmodule "evrexec.so"
loadmodule "cfgutils.so"
loadmodule "avp.so"

loadmodule "domain.so"

#!ifdef WITH_DMQ
loadmodule "dmq.so"
#!endif

loadmodule "dialog.so"
loadmodule "htable.so"

#!ifdef WITH_ANTIFLOOD
loadmodule "pike.so"
#!endif

#!ifdef WITH_AUTH
loadmodule "auth.so"
#!endif

#!ifdef WITH_XMLRPC
loadmodule "xmlrpc.so"
#!endif

#!ifdef WITH_DEBUGGER
loadmodule "debugger.so"
#!endif


# Setting module-specific parameters
# ==================================

# ----- jsonrpcs params -----
modparam("jsonrpcs", "pretty_format", 1)
modparam("jsonrpcs", "transport", 0)
modparam("jsonrpcs", "fifo_name", "/var/run/kamailio/kamailio_rpc.fifo")

# ----- tm params -----
modparam("tm", "failure_reply_mode", 3)

modparam("tm", "fr_timer", 30000)
modparam("tm", "fr_inv_timer", 120000)


modparam("tm", "reparse_on_dns_failover", 0)
modparam("tm", "cancel_b_method", 0)

#!ifdef WITH_DMQ
# ----- dmq params -----
modparam("dmq", "server_address", DMQ_SERVER_ADDRESS)
modparam("dmq", "notification_address", DMQ_NOTIFICATION_ADDRESS)
modparam("dmq", "multi_notify", 1)
modparam("dmq", "num_workers", 4)
modparam("dmq", "ping_interval", 15)
# ----- htable params -----
modparam("htable", "enable_dmq", 1)
modparam("htable", "dmq_init_sync", 1)
#!endif

#!ifdef WITH_ANTIFLOOD
# ----- pike params -----
modparam("pike", "sampling_time_unit", 2)
modparam("pike", "reqs_density_per_unit", 16)
modparam("pike", "remove_latency", 4)
# ----- pike/htable params -----
#!ifdef WITH_DMQ
modparam("htable", "htable", "ipban=>size=8;autoexpire=300;dmqreplicate=1;")
#!else
modparam("htable", "htable", "ipban=>size=8;autoexpire=300;")
#!endif
#!endif

#!ifdef WITH_REDIS_DIALOG
# ----- db_redis params -----
modparam("db_redis", "keys", "dialog=entry:hash_entry,hash_id,callid")
modparam("db_redis", "keys", "dialog_vars=entry:hash_entry,hash_id,dialog_key,dialog_value")
#!endif

#!ifdef WITH_REDIS_DIALOG
# ----- dialog params -----
modparam("dialog", "db_url", DBURL_DIALOG)
modparam("dialog", "default_timeout", 10800)
modparam("dialog", "profiles_with_value", "calllimit")
modparam("dialog", "enable_stats", 1)
modparam("dialog", "db_mode", 2)
modparam("dialog", "dlg_flag", 31)
modparam("dialog", "db_update_period", 10)
modparam("dialog", "send_bye", 1)
modparam("dialog", "dlg_match_mode", 1)
#!endif

#!ifdef WITH_XMLRPC
# ----- xmlrpc params -----
modparam("xmlrpc", "route", "XMLRPC");
modparam("xmlrpc", "url_match", "^/RPC")
#!endif

#!ifdef WITH_DEBUGGER
# ----- debugger params -----
modparam("debugger", "cfgtrace", 1)
modparam("debugger", "log_level_name", "exec")
#!endif

# ----- rr params -----
# add value to ;lr param to cope with most of the UAs
modparam("rr", "enable_full_lr", 1)
modparam("rr", "append_fromtag", 1)
modparam("rr", "enable_double_rr", 1)

# ----- http_async_client params -----
modparam("http_async_client", "workers", HTTP_ASYNC_CLIENT_WORKERS)
modparam("http_async_client", "connection_timeout", 2000)

# ----- db_text params -----
modparam("db_text", "db_mode", 1)

#!ifdef WITH_AUTH
# ----- auth params -----
modparam("auth", "algorithm", "MD5")
#!ifdef ROUTER_AUTH_SECRET
modparam("auth", "secret", ROUTER_AUTH_SECRET)
#!endif
# ----- auth/htable params -----
#!ifdef WITH_DMQ
modparam("htable", "htable", "auth=>size=16;autoexpire=60;dmqreplicate=1;")
#!else
modparam("htable", "htable", "auth=>size=16;autoexpire=60;")
#!endif
#!endif

# ----- rtpengine params -----
#!ifdef RTPENGINE_LIST
  modparam("rtpengine", "rtpengine_sock", RTPENGINE_LIST)
#!else
  modparam("rtpengine", "db_url", REG_DB_URL)
#!endif

# ----- nathelper params -----
modparam("nathelper", "natping_interval", 30)
# modparam("nathelper", "ping_nated_only", 1)
modparam("nathelper", "sipping_bflag", 7)
# To be push in variable like PyFreeBilling
modparam("nathelper", "sipping_from", "sip:pinger@librekam.io")
modparam("nathelper", "keepalive_timeout", 120)
modparam("nathelper", "sipping_method", "OPTIONS")

# params needed for NAT traversal in other modules
modparam("nathelper|registrar", "received_avp", "$avp(RECEIVED)")
modparam("nathelper", "udpping_from_path", 1)

#!ifdef WITH_UAC_REG
# ----- uac params -----
modparam("uac", "reg_db_table", "uacreg")
modparam("uac", "reg_db_url", REG_DB_URL)
modparam("uac", "reg_timer_interval", 60)
modparam("uac", "reg_retry_interval", 300)
modparam("uac", "reg_contact_addr", "$(REG_CONTACT_ADDRESS)")
modparam("uac", "reg_contact_addr", "localhost:5060")
modparam("uac", "auth_username_avp", "$avp(auser)")
modparam("uac", "auth_password_avp", "$avp(apass)")
modparam("uac", "auth_realm_avp", "$avp(arealm)")
# ----- evrexec params -----
modparam("evrexec", "exec", "name=evrexec:uacreg;wait=5000000;workers=1;")
#!endif

# ----- xhttp params -----
modparam("xhttp", "url_skip", "^/RPC2")

# ----- pv params -----
# enable or disable pike
modparam("pv", "shvset", "router_off=i:0")

# ----- domain params -----
modparam("domain", "db_url", DOMAIN_DB_URL)
modparam("domain", "register_myself", 1)

# ----- db_text params -----
modparam("db_text", "db_mode", 1)


# Included configuration files
# ============================
# import_file "routing.cfg"
# Relay request using the API
route[RELAY_API] {
    $http_req(all) = $null;
    $http_req(suspend) = 1;
    $http_req(timeout) = HTTP_API_TIMEOUT;
    $http_req(method) = "POST";
    $http_req(hdr) = "Content-Type: application/json";
    jansson_set("string", "event", "sip-routing", "$var(http_routing_query)");
    jansson_set("string", "source_ip", $avp(source_ip), "$var(http_routing_query)");
    jansson_set("int", "source_port", $avp(source_port), "$var(http_routing_query)");
#!ifdef WITH_AUTH
    jansson_set("string", "auth", 1, "$var(http_routing_query)");
    jansson_set("string", "domain", $fd, "$var(http_routing_query)");
    jansson_set("string", "username", $aU, "$var(http_routing_query)");
#!else
    jansson_set("int", "auth", 0, "$var(http_routing_query)");
#!endif
    jansson_set("string", "call_id", $ci, "$var(http_routing_query)");
    jansson_set("string", "from_name", $fn, "$var(http_routing_query)");
    jansson_set("string", "from_uri", $fu, "$var(http_routing_query)");
    jansson_set("string", "from_tag", $ft, "$var(http_routing_query)");
    jansson_set("string", "to_name", $tn, "$var(http_routing_query)");
    jansson_set("string", "to_uri", $tu, "$var(http_routing_query)");
    jansson_set("string", "to_tag", $tt, "$var(http_routing_query)");
    xlog("L_INFO","API ASYNC ROUTING REQUEST: $var(http_routing_query)\n");
    $http_req(body) = $var(http_routing_query);
    t_newtran();
    http_async_query(HTTP_API_ROUTING_ENDPOINT, "RELAY_API_RESPONSE");
}


# Relay request using the API (response)
route[RELAY_API_RESPONSE] {
    if ($http_ok && $http_rs == 200) {
        xlog("L_INFO","API ROUTING RESPONSE: $http_rb\n");
#!ifdef WITH_AUTH
        if (jansson_get("auth", $http_rb, "$var(auth)") && defined $var(auth)) {
            jansson_get("success", "$var(auth)", "$var(auth_success)");
            if (!$var(auth_success)) {
                auth_challenge("$fd", "1");
                exit;
            }
            jansson_get("password_ha1", "$var(auth)", "$avp(password)");
            if (defined $var(password) && !strempty($avp(password))) {
                if (!pv_auth_check("$fd", "$avp(password)", "1", "0")) {
                    auth_challenge("$fd", "1");
                    exit;
                } else {
                    consume_credentials();
                }
            }
            jansson_get("tenant_id", "$var(auth)", "$var(tenant_id)");
            jansson_get("carrier_trunk_id", "$var(auth)", "$var(carrier_trunk_id)");
            jansson_get("ipbx_id", "$var(auth)", "$var(ipbx_id)");
            $dlg_var(tenant_id) = $var(tenant_id);
            $dlg_var(carrier_trunk_id) = $var(carrier_trunk_id);
            $dlg_var(ipbx_id) = $var(ipbx_id);
        }
#!endif
        if (jansson_get("rtjson", $http_rb, "$var(rtjson)")) {
            if (!jansson_get("success", $var(rtjson), "$var(success)") || !$var(success)) {
                send_reply(404, "Not found");
                exit;
            } else {
                rtjson_init_routes("$var(rtjson)");
                rtjson_push_routes();
                #$avp(rtjson_routes) = 1;
                # set auth-related AVPs
                if (jansson_get("auth_username", $var(rtjson), "$var(auth_username)") &&
                    jansson_get("auth_password", $var(rtjson), "$var(auth_password)") &&
                    jansson_get("realm", $var(rtjson), "$var(realm)")) {
                    $avp(auser) = $var(auth_username);
                    $avp(apass) = $var(auth_password);
                    $avp(arealm) = $var(realm);
                }
                # relay the message

                t_on_branch("MANAGE_BRANCH");
                t_on_failure("MANAGE_FAILURE");

                route(RELAY);
                return;
            }
        }
    }
    send_reply(500, "API Not Available");
    exit;
}


# File content must be checked
# ===================================================================
# import_file "xhttp.cfg"

event_route[xhttp:request] {
  if ($hu =~ "^/rpc") {
    jansson_get("method", "$rb", "$var(rpcMethod)");
    jansson_get("id", "$rb", "$var(rpcID)");
    xlog("L_INFO","XHTTP RPC CALL - method: $var(rpcMethod) - id: $var(rpcID)\n");
    if ($var(rpcMethod) =~ "^librekam\.") {
      route(JSONRPC);
      exit;
    }

    jsonrpc_dispatch();
    exit;
  }
  else if ($hu == "/status") {
    xhttp_reply("200", "OK", "text/plain", "");
    exit;
  }

  xhttp_reply("404", "Not Found", "text/plain", "URL: $hu\r\n");
  exit;
}


route[JSONRPC] {
  if ($var(rpcMethod) == "librekam.dbtext.uacreg") {
      route(JSONRPC_DBTEXT_UACREG);

      jansson_set("string", "jsonrpc", "2.0", "$var(rpc_response)");
      jansson_set("int", "id", $var(rpcID), "$var(rpc_response)");
      jansson_set("int", "result", 1, "$var(rpc_response)");

      xhttp_reply("200", "OK", "application/json", "$var(rpc_response)");
      exit;
  }

  xhttp_reply("400", "Bad Request", "text/plain", "Method not found: $var(rpcMethod)\r\n");
  exit;
}


route[JSONRPC_DBTEXT_UACREG] {
    $http_req(all) = $null;
    $http_req(suspend) = 0;
    $http_req(timeout) = HTTP_API_TIMEOUT;
    $http_req(method) = "GET";
    xlog("L_INFO","API DBTEXT/UACREG REQUEST\n");
    http_async_query(HTTP_API_DBTEXT_UACREG_ENDPOINT, "JSONRPC_DBTEXT_UACREG_RESPONSE");
}


route[JSONRPC_DBTEXT_UACREG_RESPONSE] {
    if ($http_ok && $http_rs == 200) {
        xlog("L_INFO","API DBTEXT/UACREG RESPONSE: $http_rb\n");
        jansson_get("content", "$http_rb", "$var(dbtext_uacreg)");
        $var(dbtext_directory) = DBTEXT_DIRECTORY;
        exec_msg('mkdir -p "$var(dbtext_directory)"');
        exec_msg('echo -n "$var(dbtext_uacreg)" > "$var(dbtext_directory)/uacreg"');
        jsonrpc_exec('{"jsonrpc": "2.0", "method": "uac.reg_reload", "id": "1"}');
    }
}

# Start-up and timers
# ===================
event_route[evrexec:uacreg] {
  while(1) {
    route(JSONRPC_DBTEXT_UACREG);
    sleep("600");
  }
}



# Routing Logic
# =============
request_route {

    # log the basic info regarding this call
    xlog("L_INFO", "start|\n");
    xlog("L_INFO", "===================================================\n");
    xlog("L_INFO", " New SIP message $rm with call-ID $ci \n");
    xlog("L_INFO", "---------------------------------------------------\n");
    xlog("L_INFO", " received $pr request $rm $ou\n");
    xlog("L_INFO", " source $si:$sp\n");
    xlog("L_INFO", " from $fu\n");
    xlog("L_INFO", " to $tu\n");
    xlog("L_INFO", "---------------------------------------------------\n");
    xlog("L_INFO", "---------------------------------------------------\n");

    #!ifdef WITH_DMQ
    if ($rm == "KDMQ" && $rp == DMQ_PORT) {
        dmq_handle_message();
        exit;
    }
    #!endif

    # per request initial checks
    route(REQINIT);
    #!ifdef TESTING
    if ($shv(router_off) == 1) {
        xlog("L_NOTICE","Router is OFF..exiting!\n");
        exit;
    }
    #!endif

    # NAT detection
    route(NATDETECT);

    # OPTION processing
    if(is_method("OPTIONS") && uri==myself) {
        sl_send_reply("200","Keepalive");
        xlog("L_INFO", " Send SIP answer 200-OK - Keepalive\n");
        xlog("L_INFO", "stop|=================================================\n");
        exit;
    }

    # CANCEL processing
    if (is_method("CANCEL")) {
        xlog("L_INFO", "  $rm from $si\n");
        if (t_check_trans()) {
            route(RTPE);
            route(RELAY);
        }
        xlog("L_INFO", "  $rm from $si is not from a known transaction, drop\n");
        exit;
    }

    # handle retransmissions
    if (!is_method("ACK")) {
        if (t_precheck_trans()) {
            t_check_trans();
            exit;
        }
        t_check_trans();
    }

    # extract original source ip / port from X-forwarded-For header
    route(HANDLE_X_FORWARDED_FOR);

    # handle requests within SIP dialogs
    route(WITHINDLG);

    ### only initial requests (no To tag)

    # Check supported methos
    if (!is_method("REGISTER|INVITE|ACK|BYE|CANCEL|INFO|UPDATE")) {
        sl_send_reply("405", "Method not allowed");
        exit;
    }

    # record routing for dialog forming requests (in case they are routed)
    # - remove preloaded route headers
    remove_hf("Route");
    if (is_method("INVITE|SUBSCRIBE")) {
        record_route();
    }

    # account only INVITEs
    if (is_method("INVITE")) {
        setflag(FLT_ACC); # do accounting
    }

    # Only initial INVITE request now !

    if ($rU==$null) {
        # request with no Username in RURI
        xlog("L_INFO", "stop|-------SIP 484---------------\n");
        sl_send_reply("484","Address Incomplete");
        exit;
    }

    # enable dialog management
    if (is_method("INVITE")) {
      dlg_manage();
    }

    # clean headers
    route(REMOVEPAI);
    route(REMOVEPPI);
    route(REMOVERPID);

    # relay the messages
    route(RELAY_API);

}


# Per SIP request initial checks
route[REQINIT] {
    xlog("L_INFO", "--REQINIT--\n");

  #!ifdef WITH_ANTIFLOOD
    xlog("L_INFO", "Antiflood protection\n");
    # flood detection from same IP and traffic ban for a while
    # be sure you exclude checking trusted peers, such as pstn gateways
    # - local host excluded (e.g., loop to self)

    #!ifdef TESTING
      # Desactivate Antiflood for testing purpose
      if ($shv(pike_off) == 0) {
    #!endif

    if (src_ip!=myself) {
        if ($sht(ipban=>$si)!=$null) {
            # ip is already blocked
            xdbg("request from blocked IP - $rm from $fu (IP:$si:$sp)\n");
            xlog("L_INFO", "stop|----------------------------\n");
            exit;
        }
        if (!pike_check_req()) {
            xlog("L_ALERT","ALERT: pike blocking $rm from $fu (IP:$si:$sp)\n");
            $sht(ipban=>$si) = 1;
            xlog("L_INFO", "stop|----------------------------\n");
            exit;
        }
    }

    #!ifdef TESTING
      }
      else if ($shv(pike_off) == 1) {
          xlog("L_NOTICE","PIKE: forced to OFF!\n");
      }
    #!endif

  #!endif

    if ($ua =~ SCANNER_BLACKLIST) {
        # silent drop for scanners - uncomment next line if want to reply
        xlog("L_WARN", "end|dropping message with user-agent $ua from $si:$sp\n");
        xlog("L_INFO", "stop|----------------------------\n");
        exit;
    }

    # Code injection detection and spoofing detection
    if (is_method("INVITE|REGISTER")) {
        if($au =~ "(\=)|(\-\-)|(')|(\#)|(\%27)|(\%24)" and $au != $null) {
            xlog("L_WARN", "end|Someone from $si is doing an sql injection attack, blocking!\n");
            xlog("L_INFO", "stop|----------------------------\n");
            exit;
        }

        if($(hdr(Record-Route)[0]{nameaddr.uri}) != $si and $(hdr(Record-Route)[0]{nameaddr.uri}) != $null) {
            xlog("L_WARN", "Spoofing attack detected from $si, - rr :  $(hdr(Record-Route)[0]{nameaddr.uri}) => blocking\n");
            xlog("L_INFO", "stop|----------------------------\n");
            # exit;
        }
    }

    # initial sanity checks -- messages with
    # max_forwards==0, or excessively long requests
    if (!mf_process_maxfwd_header("10")) {
        xlog("L_WARN", "end|too much hops from $si:$sp\n");
        sl_send_reply("483","Too Many Hops");
        xlog("L_INFO", "stop|----------------------------\n");
        exit;
    }

    if (is_method("OPTIONS") && src_ip != myself) {
        sl_send_reply("200","Keepalive");
        exit;
    }

    if (!sanity_check("17895", "7")) {
        xlog("L_WARN", "end|Malformed SIP message from $si:$sp\n");
        xlog("L_INFO", "stop|----------------------------\n");
        exit;
    }

    # CVE-2018-8828
    if($(ci{s.len}) + $(hdr(CSeq){s.len}) + $(ft{s.len}) + $(sel(v.branch){s.len}) >= 254) {
        xlog("L_WARN", "end|Malformed SIP message from $si:$sp - header >=254\n");
        xlog("L_INFO", "stop|----------------------------\n");
        sl_send_reply("500", "Not accepted");
        exit;
    }
    if($(rU{s.len}) > 32) {
        xlog("L_WARN", "end|Malformed SIP message from $si:$sp - r-URI username > 32\n");
        xlog("L_INFO", "stop|----------------------------\n");
        sl_send_reply("500", "Not accepted");
        exit;
    }

    # Check for shutdown mode:
  	/* if (!has_totag() && ($sel(cfg_get.system.shutdownmode) > 0)) {
  		send_reply("503", "Server shutting down");
  		exit;
  	} */

    xlog("L_INFO", "No security issue detected : OK -> continue\n");
}

# extract original source ip / port from X-forwarded-For header
route[HANDLE_X_FORWARDED_FOR] {
    if (is_present_hf("X-Forwarded-For")) {
        $avp(source_ip) = $(hdr(X-Forwarded-For){s.select,0,:});
        $avp(source_port) = $(hdr(X-Forwarded-For){s.select,1,:});
    } else {
        $avp(source_ip) = $si;
        $avp(source_port) = $sp;
    }
}

## 9_dlguri.cfg
#-------------

# URI update for dialog requests
route[DLGURI] {
    xlog("L_INFO", "--DLGURI--\n");

    if(!isdsturiset()) {
        xlog("L_INFO", "--destination address URI (outbound proxy address) not set--\n");
        handle_ruri_alias();
        switch ($rc) {
        case -1:
            xlog("L_ERR", "--Failed to handle alias of R-URI $ru--\n");
            send_reply("400", "Bad request");
            exit;
        case 1:
            xlog("L_INFO", "--Alias param was found - Routing in-dialog $rm from $fu to $du--\n");
            break;
        case 2:
            xlog("L_INFO", "--Alias param was not found and nothing was done - Routing in-dialog $rm from $fu to $ru--\n");
            break;
        };
    }

    xlog("L_INFO", " return \n");
    return;
}

#-------------

# Handle requests within SIP dialogs
route[WITHINDLG] {
    xlog("L_INFO", "--WITHINDLG--\n");
    if (!has_totag()) return;
    # handle foreign dialogs
    if (!is_known_dlg()) {
        route(FOREIGN_DIALOG);
    }

    # sequential request withing a dialog should
    # take the path determined by record-routing
    if (loose_route()) {
        xlog("L_INFO", "loose route TRUE\n");

route(DLGURI);

        if (is_method("INVITE|UPDATE") && sdp_content() && nat_uac_test("18")) {
            route(RTPE);
        }

        if (is_method("BYE")) {
            xlog("L_INFO", "Method BYE - set acc flag\n");
            setflag(FLT_ACC); # do accounting ...
            setflag(FLT_ACCFAILED); # ... even if the transaction fails
        } else if (is_method("ACK")) {
            # ACK is forwarded statelessly
            xlog("L_INFO", "Method ACK\n");
            route(RTPE);
            route(NATMANAGE);
        } else if (is_method("NOTIFY")) {
            # Add Record-Route for in-dialog NOTIFY as per RFC 6665.
            xlog("L_INFO", "Method NOTIFY\n");
            record_route();
        }
        xlog("L_INFO", "Message has tag - no loose route -> relay\n");
        route(RELAY);
        xlog("L_INFO", "stop|----------------------------\n");
        exit;
    }

    if (is_method("ACK")) {
        if (t_check_trans()) {
            # no loose-route, but stateful ACK;
            # must be an ACK after a 487
            # or e.g. 404 from upstream server
            xlog("L_INFO", "stop|---no loose-route, but stateful ACK\n");
            route(RELAY);
            xlog("L_INFO", "stop|----------------------------\n");
            exit;
        } else {
            # ACK without matching transaction ... ignore and discard
            xlog("L_INFO", "stop|---ACK without matching transaction ... ignore and discard\n");
            xlog("L_INFO", "stop|----------------------------\n");
            exit;
        }
    }
    sl_send_reply("404","Not here");
    exit;
}

route[FOREIGN_DIALOG] {
    xlog("L_INFO", "FOREIGN_DIALOG - loading dialog from DB for ci: $(ci) ...\n");

    dlg_db_load_callid($ci);
    if (is_known_dlg()) {
        dlg_manage();
        return;
    }

    send_reply('400', "Bad Request");
    exit;
}


# Caller NAT detection
route[NATDETECT] {
    xlog("L_INFO", "--start NATDETECT process--\n");
    force_rport();

    if (nat_uac_test("19")) {
        xlog("L_INFO", "----uac NAT test 19 true\n");

        if (is_method("REGISTER")) {
            xlog("L_INFO", "----Method REGISTER -> fix nat\n");
            fix_nated_register();
        } else {
            if (is_first_hop())
                xlog("L_INFO", "----First hop - set contact alias\n");
                set_contact_alias();
        }

        xlog("L_INFO", "----Set flag NATS\n");
        setflag(FLT_NATS);
    }
    xlog("L_INFO", " return \n");
    return;
}


# NAT management control
route[NATMANAGE] {
    xlog("L_INFO", "--NATMANAGE--\n");
    # Set FLB_NATB? Only in within-dialog request with nat=yes on Route header initiated by us
    if (is_request() && has_totag()) {
        xlog("L_INFO", "----SIP Request - to-tag found--\n");
        if(check_route_param("nat=yes")) {
            setbflag(FLB_NATB);
            xlog("L_INFO", "----SIP Request - route param nat=yes--\n");
        } else {
            xlog("L_INFO", "----SIP Request - no route param nat=yes--\n");
        }
    }

    # Return unless FLT_NATS or FLB_NATB are set
    if (!(isflagset(FLT_NATS) || isbflagset(FLB_NATB))) return;

    /*     # Fix sdp if UA behind NAT
    if(has_body("application/sdp") && nat_uac_test("8")) {
        xlog("L_INFO", "----Fix nated sdp\n");
        fix_nated_sdp("10");
    } */

    # Add nat=yes in record-route? Only in initial requests when called from branch_route
    if (is_request() && !has_totag() && t_is_branch_route()) {
        add_rr_param(";nat=yes");
        xlog("L_INFO", "----SIP Request - to-tag not found - Branch route--\n");
        xlog("L_INFO", "----add nat=yes to Record-Route header--\n");
    }

    # Add contact alias? Only to replies with NATB set and first hop
    if (is_reply() && isbflagset(FLB_NATB) && is_first_hop()) {
        set_contact_alias();
        xlog("L_INFO", "----SIP Reply - FLB_NATB set - First hop--\n");
        xlog("L_INFO", "----add nat=yes to Record-Route header--\n");
    }

    xlog("L_INFO", "----Return \n");
    return;
}


# Wrapper for relaying requests
route[RELAY] {
    # enable additional event routes for forwarded requests
    # - serial forking, RTP relaying handling, a.s.o.
    xlog("L_INFO", "--RELAY--\n");
#    if (is_method("INVITE|BYE|UPDATE|CANCEL|ACK")) {
#        dlg_manage();
#    }
    if (is_method("INVITE|BYE|SUBSCRIBE|UPDATE")) {
        if (!t_is_set("branch_route")) {
            t_on_branch("MANAGE_BRANCH");
        }
    }
    if (is_method("INVITE|SUBSCRIBE|UPDATE")) {
        if (!t_is_set("onreply_route")) {
            t_on_reply("MANAGE_REPLY");
        }
    }


    if (is_method("INVITE")) {
        if (!t_is_set("failure_route")) {
            t_on_failure("MANAGE_FAILURE");
        }
    }

    if (!t_relay()) {
        xlog("L_INFO", "end|unable to relay message\n");
        sl_reply_error();
    } else {
        xlog("L_INFO", "pass|successfull relay $du\n");
    }

    xlog("L_INFO", "stop|----------------------------\n");
    exit;
}

# Get and remove PAI
route[REMOVEPAI] {
    xlog("L_INFO", "--REMOVEPAI--\n");

    if (is_present_hf("P-Asserted-Identity")) {
        xlog("L_INFO", " PAI detected\n");
        $avp(s:paicallernum)=$(hdr(P-Asserted-Identity){tobody.user});
        if ($avp(s:paicallernum)=~"^\+") {
            # strip leading +
            xlog("L_INFO", "Caller leading + \n");
            $avp(s:paicallernum)=$(avp(s:paicallernum){s.strip,1});
        }
        xlog("L_INFO", " Retrieved CallerId ($avp(s:paicallernum)) from P-Asserted-Identity header \r\n");
        xlog("L_INFO", " Remove PAI header \n");
        remove_hf("P-Asserted-Identity");

        $avp(s:callernum)=$avp(s:paicallernum);
    }
}

# Get and remove PPI
route[REMOVEPPI] {
    xlog("L_INFO", "--REMOVEPPI--\n");

    if (is_present_hf("P-Preferred-Identity")) {
        xlog("L_INFO", " PPI detected\n");
        $avp(s:ppicallernum)=$(hdr(P-Preferred-Identity){tobody.user});
        if ($avp(s:ppicallernum)=~"^\+") {
            # strip leading +
            xlog("L_INFO", "Caller leading + \n");
            $avp(s:ppicallernum)=$(avp(s:ppicallernum){s.strip,1});
        }
        xlog("L_INFO", " Retrieved CallerId ($avp(s:ppicallernum)) from P-Preferred-Identity header \r\n");
        xlog("L_INFO", " Remove PPI header \n");
        remove_hf("P-Preferred-Identity");

        $avp(s:callernum)=$avp(s:ppicallernum);
    }
}

# Get and remove RPID
route[REMOVERPID] {
    xlog("L_INFO", "--REMOVEPID--\n");

    if (is_present_hf("Remote-Party-ID")) {
        xlog("L_INFO", " RPID detected\n");
        $avp(s:rpidcallernum)=$(hdr(Remote-Party-ID){tobody.user});
        xlog("L_INFO", " Retrieved CallerId ($avp(s:rpidcallernum)) from Remote-Party-ID header \r\n");
        xlog("L_INFO", " Remove RPID header \n");
        remove_hf("Remote-Party-ID");
    }

}


# Manages RTP Engine
route[RTPE] {
    if (!is_method("INVITE|UPDATE|ACK|BYE|CANCEL")) return;

    if (is_method("ACK") && !has_body("application/sdp")) return;

    $var(common_opts) = 'replace-session-connection replace-origin';

    if (nat_uac_test("18")) {
        xlog("L_INFO", "-- RTPENGINE: NAT detected, do not trust SDP addresses\n");
        $var(symmetry) = 'SIP-source-address';
    } else {
        xlog("L_INFO", "-- RTPENGINE: No NAT detected, trust SDP addresses\n");
        $var(symmetry) = 'trust-address';
    }

    $var(wsopts) ='ICE=remove RTP/AVP';
    $var(interfaces) = "direction=external direction=external";

    if (sdp_content()){
        xlog("L_INFO", "-- RTPENGINE: rtpengine_manage [$var(common_opts) $var(symmetry) $var(wsopts) $var(interfaces)]\n");
        if (is_method("INVITE")) {
            rtpengine_offer("$var(common_opts) $var(symmetry) $var(wsopts) $var(interfaces)");
        } else {
            rtpengine_manage("$var(common_opts) $var(symmetry) $var(wsopts) $var(interfaces)");
        }
    }
}

# Manage outgoing branches
branch_route[MANAGE_BRANCH] {
    xlog("L_INFO", "--MANAGE_BRANCH--\n");
    xlog("L_INFO", "--new branch [$T_branch_idx] to $ru--\n");
    xdbg("new branch [$T_branch_idx] to $ru\n");

        rtjson_update_branch();
route(NATMANAGE);
    route(RTPE);

}


# Manage incoming replies
onreply_route[MANAGE_REPLY] {
    xdbg("incoming reply\n");
    xlog("L_INFO", "-- Response: '$rs $rr' to '$cs $rm' from '$fu' ($si:$sp) [$proto]\n");

    if(nat_uac_test("18")) {
      force_rport();
      set_contact_alias();
    }
if(status=~"18[03]") {
        xlog("L_INFO", "--ringing or session in progress--\n");
    }

    if(status=~"[12][0-9][0-9]") {
        route(RTPE);
        route(NATMANAGE);
    }

}


# Manage failure routing cases
failure_route[MANAGE_FAILURE] {
    xlog("L_INFO", "-- Failure: '$rs $rr' to '$cs $rm' from '$fu' ($si:$sp) [$proto]\n");
route(NATMANAGE);

    if (t_is_canceled()) {
        xlog("L_INFO", "--MANAGE_FAILURE: t_is_canceled, exit here\n");
        exit;
    }
    if (t_check_status("401|407")) {
        uac_auth();
        t_relay();
        exit;
    }


    if (rtjson_next_route()) {
        t_on_branch("MANAGE_BRANCH");
        t_on_failure("MANAGE_FAILURE");
        route(RELAY);
        exit;
    }

}

# Executed when dialog is confirmed with 2XX response code
event_route[dialog:start] {
    xlog("L_INFO", "-- Dialog starts with $ci\n");
}

# Executed when dialog is ended with BYE or timeout
event_route[dialog:end] {
    xlog("L_INFO", "-- Dialog ended, delete keys from dialogs htable starting with $ci\n");
}
