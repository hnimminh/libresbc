--
-- nglog.lua
--
-- The Initial Developer of the Original Code is
-- Minh Minh <hnimminh at[@] outlook dot[.] com>
-- Inspired from rxi/log.lua
-- Portions created by the Initial Developer are Copyright (C) the Initial Developer.
-- All Rights Reserved.
--

nglog = { _version = '0.1.0' }
nglog.color   = false
nglog.level   = 'info'
nglog.stacks  = { console=true, file=nil, syslog=nil}
nglog.host    = nil
nglog.name    = nil

local attributes = {
    { name = 'emerg',     color = '\27[35m', }, -- 0 emerg system is unusable
    { name = 'alert',     color = '\27[35m', }, -- 1 alert action must be taken immediately
    { name = 'critical',  color = '\27[35m', }, -- 2 critical conditions
    { name = 'error',     color = '\27[31m', }, -- 3 error conditions
    { name = 'warning',   color = '\27[33m', }, -- 4 warning conditions
    { name = 'notice',    color = '\27[34m', }, -- 5 normal but significant condition
    { name = 'info',      color = '\27[32m', }, -- 6 informational
    { name = 'debug',     color = '\27[36m', }, -- 7 debug-level messages
}

local levels = {}
for i, attribute in ipairs(attributes) do
    levels[attribute.name] = i-1
end

for i, attribute in ipairs(attributes) do
    local _LEVEL = attribute.name:upper()

    nglog[attribute.name] = function(msg, ...)
        -- quick fast: if given log level is smaller than function log level
        if levels[nglog.level] < i-1 then
            return
        end

        -- default log string
        local logstr
        if nglog.stacks.file or not nglog.color then
            logstr = string.format('%s %s %s %s  %s',
                        os.date('%Y-%m-%dT%H:%M:%S%z'), nglog.host, nglog.name, _LEVEL, string.format(msg..'\n', ...)
                    )
        end

        -- print out to syslog
        if nglog.stacks.syslog then -- syslog FACILITY = N*8; syslog.LOG_LOCAL6=22*8=176
            syslog = require("posix.syslog")
            syslog.openlog(nglog.name, syslog.LOG_PID, tonumber(nglog.stacks.syslog) or 176)
            syslog.syslog(i-1, string.format(msg..'\n', ...))
        end

        -- print out log to console
        if nglog.stacks.console then
            if nglog.color then
                print(string.format('%s%s %s %s %s%s  %s',
                    attribute.color, os.date('%Y-%m-%dT%H:%M:%S%z'), nglog.host, nglog.name, _LEVEL, '\27[0m', string.format(msg..'\n', ...))
                )
            else
                print(logstr)
            end
        end

        -- print out log to file
        if nglog.stacks.file then
            local fp = io.open(nglog.stacks.file, 'a')
            fp:write(logstr)
            fp:close()
        end
    end
end

return nglog
