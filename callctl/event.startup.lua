dofile("{{rundir}}/callctl/utilities.lua")

---------------------------------------------------------------------------
local unpack = _G.unpack or table.unpack

local function fire_startup_event()
    local key = 'event:callengine:startup:'..NODEID
    local value = json.encode({action='restart', prewait=0, requestid='uuid-of-callengine-startup-event'})
    rdbconn:lpush(key, value)
    logify('module', 'callctl', 'space', 'event:startup', 'action', 'fire_startup_event', 'key', key, 'value', value)
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
    logify('module', 'callctl', 'space', 'event:startup', 'action', 'clean_node_capacity', 'node', NODEID)
end

local function environment()
    local clustermebers = join(rdbconn:smembers('cluster:members'))
    freeswitch.setGlobalVariable("CLUSTERMEMBERS", clustermebers)
    logify('module', 'callctl', 'space', 'event:startup', 'action', 'environment', 'CLUSTERMEMBERS', clustermebers)
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
    logger("module=callctl, space=event:startup, action=exception, error="..tostring(error))
end
---- close log ----
syslog.closelog()
