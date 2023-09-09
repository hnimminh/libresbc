--
-- callng:event.unauth.lua
--
-- The Initial Developer of the Original Code is
-- Minh Minh <hnimminh at[@] outlook dot[.] com>
-- Portions created by the Initial Developer are Copyright (C) the Initial Developer.
-- All Rights Reserved.
--

require("callng.utilities")
---------------------------------------------------------------------------

local function unauth()
    local profilename = event:getHeader("profile-name")
    local user_agent = event:getHeader("user-agent")
    local network_ip = event:getHeader("network-ip")
    log.warning('module=callng, space=event:unauth, action=queue-block, profilename=%s, user_agent=%s, network_ip=%s,', profilename, user_agent, network_ip)
end
---------------------******************************---------------------
---------------------*****|       MAIN       |*****---------------------
---------------------******************************---------------------
local result, error = pcall(unauth)
if not result then
    logger("module=callng, space=event:unauth, action=exception, error=%s", error)
end
---- close log ----
syslog.closelog()
