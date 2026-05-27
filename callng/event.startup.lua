--
-- callng:event.startup.lua
--
-- The Initial Developer of the Original Code is
-- Minh Minh <hnimminh at[@] outlook dot[.] com>
-- Portions created by the Initial Developer are Copyright (C) the Initial Developer.
-- All Rights Reserved.
--

require("callng.callfunc")
---------------------------------------------------------------------------

local function recovery()
    local CRC_CAPABILITY = (os.getenv("CRC_CAPABILITY") or 'FALSE'):upper()
    if ismeberof({'TRUE', 'YES', '1'}, CRC_CAPABILITY) then
        local ack = fsapi:executeString('fsctl recover')
        log.info('module=callng, space=event:startup, action=recover, ack=%s', ack)
    else
        local ack = fsapi:executeString('unload mod_pgsql')
        log.info('module=callng, space=event:startup, action=depgsql, ack=%s', ack)
    end
end

---------------------******************************---------------------
---------------------*****|       MAIN       |*****---------------------
---------------------******************************---------------------
local function cleanup_stale_concurentcalls()
    -- FreeSWITCH startup: remove stale call-tracking keys left by a hard kill/crash
    local pattern = 'realtime:concurentcalls:*:*:' .. NODEID
    local cursor = '0'
    repeat
        local res = rdbconn:scan(cursor, 'MATCH', pattern, 'COUNT', 100)
        cursor = res[1]
        for _, key in ipairs(res[2]) do
            rdbconn:del(key)
            log.info('module=callng, space=event:startup, action=cleanup_stale_concurentcalls, key=%s', key)
        end
    until cursor == '0'
end

local function main()
    cleanup_stale_concurentcalls()
    recovery()
end
-----
local result, error = pcall(main)
if not result then
    log.critical("module=callng, space=event:startup, action=exception, error=%s", error)
end
