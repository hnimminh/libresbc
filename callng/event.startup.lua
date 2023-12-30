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
local function main()
    recovery()
end
-----
local result, error = pcall(main)
if not result then
    log.critical("module=callng, space=event:startup, action=exception, error=%s", error)
end
