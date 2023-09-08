--
-- callng:main.lua
--
-- The Initial Developer of the Original Code is
-- Minh Minh <hnimminh at[@] outlook dot[.] com>
-- Portions created by the Initial Developer are Copyright (C) the Initial Developer.
-- All Rights Reserved.
--

-- REQUIRE
socket = require("socket")
syslog = require("posix.syslog")
json = require("json")
redis = require("redis")
random = math.random

require("callng.configuration")
log = require("callng.nglog")
log.stacks, log.host, log.name = {console=false, file=nil, syslog=true}, NODEID, 'libresbc'

unpack = _G.unpack or table.unpack
__space__ = ' '
__comma__ = ','
----------------------------------------------------------------------------
-- REDIS CONNECTION
rdbconn = nil
rdbstate, rdberror = pcall(redis.connect, REDIS_HOST, REDIS_PORT, REDIS_TIMEOUT)
if rdbstate then
    rdbconn = redis.connect(REDIS_HOST, REDIS_PORT, REDIS_TIMEOUT)
    if REDIS_DB ~= 0 then rdbconn:select(REDIS_DB) end
    if REDIS_PASSWORD then rdbconn:auth(REDIS_PASSWORD) end
end
---------------------******************************--------------------------
---------------------****|  FUNDAMENTAL FUNCTION   |****---------------------
---------------------******************************--------------------------

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

function delogify(...)
    local arg = {...}
    local message = arg[1]..'='..tostring(arg[2])
    for i=3,#arg,2 do message = message..', '..arg[i]..'='..tostring(arg[i+1]) end
    -- write log
    dlogger(message)
end

-------------------------------------------------------------------------
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

--- performance function compare to table.insert
function arrayinsert(array, item)
   array[#array+1] = item
end


function topybool(data)
    local datatype = type(data)
    if datatype == 'nil' then return false
    elseif datatype == 'string' then
        if #data == 0 then return false
        else return true end
    elseif datatype == 'table' then
        if next(data)== nil then return false
        else return true end
    elseif datatype == 'number' then
        if data == 0 then return false
        else return true end
    else
        return true
    end
end

function toboolean(data)
    local datatype = type(data)
    if datatype=='string' then
        if string.lower(data) == 'true' then return true
        else return false end
    elseif datatype=='boolean' then
        return data
    else
        return false
    end
end

function split(inputstr, separator)
    if not separator then separator = __comma__ end
    local array = {}
    local newstr = inputstr..separator
    for element in newstr:gmatch("([^"..separator.."]*)"..separator) do arrayinsert(array, element) end
    return array
end

function join(array, separator)
    if not separator then separator = __comma__ end
    return table.concat(array, separator)
end

function rulejoin(array)
    return '['..table.concat(array, __comma__)..']'
end

function startswith(originstr, startstr)
    return originstr:sub(1, #startstr) == startstr
end

function randompick(intable)
    return intable[random(#intable)]
end


function fieldjsonify(data)
    if type(data)=='string' then
        if startswith(data, ':bool:') then
            if data == ':bool:true' then return true
            else return false end
        elseif startswith(data, ':int:') then return tonumber(data:sub(6,#data))
        elseif startswith(data, ':float:') then return tonumber(data:sub(8,#data))
        elseif startswith(data, ':list:') then
            if data==':list:' then return {}
            else return split(data:sub(7,#data)) end
        elseif startswith(data, ':json:') then return json.decode(data:sub(7,#data))
        elseif startswith(data, ':none:') then return nil
        else return data end
    else
        return data
    end
end


function jsonhash(data)
    if type(data)=='table' then
        for key, value in pairs(data) do
            if type(value)=='string' then
                if startswith(value, ':bool:') then
                    if value == ':bool:true' then data[key] = true
                    else data[key] = false end
                elseif startswith(value, ':int:') then data[key] = tonumber(value:sub(6,#value))
                elseif startswith(value, ':float:') then data[key] = tonumber(value:sub(8,#value))
                elseif startswith(value, ':list:') then
                    if value==':list:' then data[key] = {}
                    else data[key] = split(value:sub(7,#value)) end
                elseif startswith(value, ':json:') then data[key] = json.decode(value:sub(7,#value))
                elseif startswith(value, ':none:') then data[key] = nil
                else end
            else end
        end
    end
    return data
end


----------------------------------------------------------------------------
function arraycomplement(ai, aj)
    local a = {}
    for i=1,#ai do
        local duplication = false
        for j=1,#aj do
            if ai[i] == aj[j] then
                duplication = true
                break
            end
        end
        if not duplication then a[#a+1] = ai[i] end
    end
    return a
end

---------------------------------------------------------------------------- GET KEY
function intconkey(name, direction)
    if direction == INBOUND then
        return 'intcon:in:'..name
    else
        return 'intcon:out:'..name
    end
end

function concurentcallskey(name)
    return 'realtime:concurentcalls:'..name..':'..NODEID
end

----------------------------------------------------------------------------
function writefile(filename, stringdata)
    -- a: Append mode that opens an existing file or creates a new file for appending.
    -- w: Write enabled mode that overwrites the existing file or creates a new file.
    local file = io.open(filename, 'a')
    file:write(stringdata, '\n')
    -- closes the open file
    file:close()
end
