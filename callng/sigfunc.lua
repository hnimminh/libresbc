--
-- callng:sigfunc.lua
--
-- The Initial Developer of the Original Code is
-- Minh Minh <hnimminh at[@] outlook dot[.] com>
-- Portions created by the Initial Developer are Copyright (C) the Initial Developer.
-- All Rights Reserved.
-- ------------------------------------------------------------------------------------------------------------------------------------------------

require("callng.utilities")

PATTERN = '^[%w_%.%-]$'

function digestauth(authuser, domain)
    if not authuser:match(PATTERN) or not domain:match(PATTERN) then
        return -1
    end
    local a1hash = rdbconn:hget('access:dir:usr:'..domain..':'..authuser, 'a1hash')
    if a1hash then
        return 1, a1hash
    else
        return 0
    end
    return -2
end

function ipauth(ipaddr, domain)
    if not domain:match(PATTERN) then
        return -1
    end
    local port, transport = rdbconn:hmget('access:dir:ip:'..domain..':'..ipaddr, {'port', 'transport'})
    if port and transport then
        return 1, port, transport
    else
        return 0
    end
    return -2
end

function antiattack()
end

function bruteforce()
end

