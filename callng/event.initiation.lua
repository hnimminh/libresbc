--
-- callng:event.initiation.lua
--
-- The Initial Developer of the Original Code is
-- Minh Minh <hnimminh at[@] outlook dot[.] com>
-- Portions created by the Initial Developer are Copyright (C) the Initial Developer.
-- All Rights Reserved.
--

require("callng.utilities")

---------------------------------------------------------------------------
local function clean_node_capacity()
    local PATTERN = 'realtime:capacity:*:'..NODEID
    local next, capacity_keys = unpack(rdbconn:scan(0, {match=PATTERN, count=SCAN_COUNT}))
    while (tonumber(next) > 0)
    do
        local batchs = nil
        next, batchs = unpack(rdbconn:scan(next, {match=PATTERN, count=SCAN_COUNT}))
        capacity_keys = mergetable(capacity_keys, batchs)
    end
    ---
    rdbconn:pipeline(function(p)
        for i=1, #capacity_keys do
            p:del(capacity_keys[i])
        end
    end)
    ---
    log.info('module=callng, space=event:initiation, action=clean_node_capacity, node=%s', NODEID)
end

---------------------------------------------------------------------------
local function environment()
    local clustermebers = join(rdbconn:smembers('cluster:members'))
    freeswitch.setGlobalVariable("CLUSTERMEMBERS", clustermebers)
    local clustername = rdbconn:get('cluster:name')
    freeswitch.setGlobalVariable("CLUSTERNAME", clustername)
    log.info('module=callng, space=event:initiation, action=environment, CLUSTERNAME=%s, CLUSTERMEMBERS=%s', clustername, clustermebers)
end

---------------------------------------------------------------------------
local function register()
    local liberator_api_url = freeswitch.getGlobalVariable("liberator_api_url")
    local eslhost = freeswitch.getGlobalVariable("eslhost")
    local eslport = freeswitch.getGlobalVariable("eslport")
    local eslpassword = freeswitch.getGlobalVariable("eslpassword")

    local url = liberator_api_url .. "/discovery"
    local _payload = {
        nodeid = NODEID,
        ipaddr = eslhost,
        port = eslport
    }
    local payload = _payload['password'] = eslpassword

    local headers = {
        ["content-type"] = "application/json",
        ["content-length"] = #bodyjson
    }

    local res, code, _, _, body = httprequest("POST", url, json.encode(payload), headers)
    if res==nil or code~=200 then
        log.error('module=callng, space=event:initiation, action=register, url=%s, request=%s, error=%s', url, json.encode(_payload), code)
    else
        log.debug('module=callng, space=event:initiation, action=register, url=%s, request=%s, response=%s', url, json.encode(_payload), body)
    end
end

-----------------**********************************--------------------
-----------------*****|   STARTUP-SCRIPT     |*****--------------------
-----------------**********************************--------------------
local function main()
    -- NO NEED TO CLEAN CPS, AS IT JUST ONE-TIME-ATTEMPT
    -- CLEAN CAPACITY AS IT IS LONG-LIVE-TIME-ATTEMP
    -- luarun ~freeswitch.consoleLog('debug','callflow run on '.._VERSION)
    clean_node_capacity()
    environment()
    register()
end

---------------------******************************---------------------
---------------------*****|       MAIN       |*****---------------------
---------------------******************************---------------------
local result, error = pcall(main)
if not result then
    log.critical("module=callng, space=event:initiation, action=exception, error=%s", error)
end
