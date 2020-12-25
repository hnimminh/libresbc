dofile("/opt/libresbc/run/callengine/configuration.lua")

-- REQUIRE
redis = require("redis")
socket = require("socket")
syslog = require("posix.syslog")
json = require("json")
luuid = require("lua_uuid")
random = math.random

-- REDIS CONNECTION
rdbconn = nil
rdbstate, rdberror = pcall(redis.connect, REDIS_HOST, REDIS_PORT, REDIS_TIMEOUT)
if rdbstate then
    rdbconn = redis.connect(REDIS_HOST, REDIS_PORT, REDIS_TIMEOUT)
    if REDIS_DB ~= 0 then rdbconn:select(REDIS_DB) end
    if REDIS_PASSWORD then rdbconn:auth(REDIS_PASSWORD) end
end
-------------------------------------------------------------------------
--* FUNDAMENTAL FUNTION
-------------------------------------------------------------------------

function logger(msg)
    syslog.openlog('libresbc', syslog.LOG_PID, syslog.LOG_LOCAL6)
    syslog.syslog(syslog.LOG_INFO, msg)
end

function dlogger(msg)
    syslog.openlog('libresbc', syslog.LOG_PID, syslog.LOG_LOCAL6)
    syslog.syslog(syslog.LOG_DEBUG, msg)
end


function logify(...)
    local arg = {...}
    local message = arg[1]..'='..tostring(arg[2])
    for i=3,#arg,2 do message = message..', '..arg[i]..'='..tostring(arg[i+1]) end 
    -- write log
    logger(message)
end

function dlogify(...)
    local arg = {...}
    local message = arg[1]..'='..tostring(arg[2])
    for i=3,#arg,2 do message = message..', '..arg[i]..'='..tostring(arg[i+1]) end 
    -- write log
    dlogger(message)
end

-------------------------------------------------------------------------

function dialmeta(intable)
    return "{"..table.concat(intable, ",") .."}"
end

function ismeberof(intable, value)
	for i=1, #intable do
		if value == intable[i] then return true end
	end
	return false
end

function mergetable(t1,t2)
    for i=1,#t2 do
        t1[#t1+i] = t2[i]
    end
    return t1
end

function topybool(data)
    local datatype = type(data)
    if datatype == 'nil' then return false end
    if datatype == 'string' or datatype == 'table' then
        if #data == 0 then return false
        else return true end
    end
    if datatype == 'number' then
        if data == 0 then return false
        else return true end
    end

    return true
end

function split(inputstr, separator)
    local array = {}
    local newstr = inputstr..separator
    for element in newstr:gmatch("([^"..separator.."]*)"..separator) do table.insert(array, element) end
    return array
end

function join(array, separator)
    return table.concat(array, separator)
end

function startswith(originstr, startstr)
    return originstr:sub(1, #startstr) == startstr
end

function randompick(intable)
    return intable[random(#intable)]
end