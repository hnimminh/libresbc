--
-- callng:event.startup.lua
-- 
-- The Initial Developer of the Original Code is
-- Minh Minh <hnimminh at[@] outlook dot[.] com>
-- Portions created by the Initial Developer are Copyright (C) the Initial Developer. 
-- All Rights Reserved.
--

require("callng.utilities")
---------------------------------------------------------------------------

local function fire_startup_event()
    local channel = 'NG:STARTUP:'..NODEID
    local data = json.encode({portion='ngstartup', requestid='00000000-0000-0000-0000-000000000000'})
    rdbconn:publish(channel, data)
    logify('module', 'callng', 'space', 'event:startup', 'action', 'fire_startup_event', 'channel', channel, 'data', data)
end

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
    logify('module', 'callng', 'space', 'event:startup', 'action', 'clean_node_capacity', 'node', NODEID)
end

local function environment()
    local clustermebers = join(rdbconn:smembers('cluster:members'))
    freeswitch.setGlobalVariable("CLUSTERMEMBERS", clustermebers)
    local clustername = rdbconn:get('cluster:name')
    freeswitch.setGlobalVariable("CLUSTERNAME", clustername)
    logify('module', 'callng', 'space', 'event:startup', 'action', 'environment', 'CLUSTERMEMBERS', clustermebers, 'CLUSTERNAME', clustername)
end

-----------------**********************************--------------------
-----------------*****|   STARTUP-SCRIPT     |*****--------------------
-----------------**********************************--------------------
local function main()
    -- NO NEED TO CLEAN CPS, AS IT JUST ONE-TIME-ATTEMPT
    -- CLEAN CAPACITY AS IT IS LONG-LIVE-TIME-ATTEMP
    -- luarun ~freeswitch.consoleLog('debug','callflow run on '.._VERSION)
    clean_node_capacity()
    fire_startup_event()
    environment()
end

---------------------******************************---------------------
---------------------*****|       MAIN       |*****---------------------
---------------------******************************---------------------
local result, error = pcall(main)
if not result then
    logger("module=callng, space=event:startup, action=exception, error="..tostring(error))
end
---- close log ----
syslog.closelog()
