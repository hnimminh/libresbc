dofile("configuration.lua")
dofile("utilities.lua")

---------------------------------------------------------------------------
local unpack = _G.unpack or table.unpack

local function fire_infra_event()
    local key = 'event:infra:fsengine:'..NODENAME
    local value = json.encode({subevent='restart', prewait=0, requestid=luuid()})
    rdbconn:lpush(key, value)
    logify('module', 'callctl', 'space', 'startup', 'action', 'fire_infra_event', 'key', key, 'value', value)
end

local function clean_node_capacity()
    local _CAPACITY_KEY_PATTERN = 'call:capacity:*:'..NODENAME
    local next, capacity_keys = unpack(rdbconn:scan(0, {match=_CAPACITY_KEY_PATTERN, count=SCAN_COUNT}))
    while (tonumber(next) > 0)
    do
        local batchs = nil
        next, batchs = unpack(rdbconn:scan(next, {match=_CAPACITY_KEY_PATTERN, count=SCAN_COUNT}))
        capacity_keys = mergetable(capacity_keys, batchs)
    end
    ---
    rdbconn:pipeline(function(p)
        for i=1, #capacity_keys do
            p:del(capacity_keys[i])
        end
    end)
    ---
    logify('module', 'callctl', 'space', 'startup', 'action', 'clean_node_capacity', 'node', NODENAME)
end

-----------------**********************************--------------------
-----------------*****|   STARTUP-SCRIPT     |*****--------------------
-----------------**********************************--------------------
local function main()
    -- NO NEED TO CLEAN CPS, AS IT JUST ONE-TIME-ATTEMPT
    -- CLEAN CAPACITY AS IT IS LONG-LIVE-TIME-ATTEMP
    -- luarun ~freeswitch.consoleLog('debug','callflow run on '.._VERSION)
    clean_node_capacity()
    fire_infra_event()
end

---------------------******************************---------------------
---------------------*****|       MAIN       |*****---------------------
---------------------******************************---------------------
local result, error = pcall(main)
if not result then
    logger("module=callctl, space=startup, action=exception, error="..tostring(error))
end
---- close log ----
syslog.closelog()
