dofile("{{rundir}}/enginectl/utilities.lua")
---------------------------------------------------------------------------

local function unauth()
    local profilename = event:getHeader("profile-name")
    local user_agent = event:getHeader("user-agent")
    local network_ip = event:getHeader("network-ip")
    logify('module', 'enginectl', 'space', 'event:unauth', 'action', 'queue-block', 'profilename', profilename, 'user_agent', user_agent, 'network_ip', network_ip)
end
---------------------******************************---------------------
---------------------*****|       MAIN       |*****---------------------
---------------------******************************---------------------
local result, error = pcall(unauth)
if not result then
    logger("module=enginectl, space=event:unauth, action=exception, error="..tostring(error))
end
---- close log ----
syslog.closelog()
