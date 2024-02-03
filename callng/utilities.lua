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
require("callng.configuration")
log = require("callng.nglog")
log.stacks = {
    console =   LOGSTACK_CONSOLE,
    file    =   LOGSTACK_FILE,
    syslog  =   LOGSTACK_SYSLOG
}
log.level   = LOGLEVEL
log.host    = NODEID
log.name    = LIBRESBC

random = math.random
unpack = _G.unpack or table.unpack
__space__ = ' '
__comma__ = ','
__empty__ = ''
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

function endswith(originstr, endstr)
    return originstr:sub(-#endstr) == endstr
end

function randompick(intable)
    return intable[random(#intable)]
end

function tosets(array)
    local hash = {}
    local result = {}
    for _,v in ipairs(array) do
        if not hash[v] then
            result[#result+1] = v
            hash[v] = true
        end
    end
    return result
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
--- switch log
swlog = {
    debug    = function(text, ...) freeswitch.consoleLog("debug",   string.format(text.."\n", ...)) end,
    info     = function(text, ...) freeswitch.consoleLog("info",    string.format(text.."\n", ...)) end,
    notice   = function(text, ...) freeswitch.consoleLog("notice",  string.format(text.."\n", ...)) end,
    warning  = function(text, ...) freeswitch.consoleLog("warning", string.format(text.."\n", ...)) end,
    error    = function(text, ...) freeswitch.consoleLog("err",     string.format(text.."\n", ...)) end,
    critical = function(text, ...) freeswitch.consoleLog("crit",    string.format(text.."\n", ...)) end,
    alert    = function(text, ...) freeswitch.consoleLog("alert",   string.format(text.."\n", ...)) end,
    emerg    = function(text, ...) freeswitch.consoleLog("alert",   string.format(text.."\n", ...)) end
}
log.emlt = swlog
----------------------------------------------------------------------------

-- CURL REQUEST
function curlget(url, headers)
    local status, body
    local curl = require("cURL")
    local c = curl.easy{
        url = url,
        httpheader = headers,
        [curl.OPT_TIMEOUT] = 5,
        writefunction = function(r) body = r end
    }

    local ok, err = pcall(function() c:perform() end)
    if not ok then
        return ok, err, body, status
    end
    status = c:getinfo_response_code()
    c:close()
    return ok, err, body, status
end

-- HTTP REQUEST
local function httprequest(method, url, payload, headers)
    local http
    if startswith(url, "https") then
        http = require("ssl.https")
    else
        http = require("socket.http")
    end
    http.TIMEOUT = 5

    local body = {}
    local ltn12 = require("ltn12")
    local result, code, headers, status = http.request{
        url = url,
        method = method,
        headers = headers,
        source = ltn12.source.string(payload),
        sink = ltn12.sink.table(body)
    }

    return result, code, headers, status, body
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
