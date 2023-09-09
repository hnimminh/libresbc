--
-- callng:callfunc.lua
--
-- The Initial Developer of the Original Code is
-- Minh Minh <hnimminh at[@] outlook dot[.] com>
-- Portions created by the Initial Developer are Copyright (C) the Initial Developer.
-- All Rights Reserved.
--

require("callng.utilities")
---------------------******************************--------------------------
---------------------****|  CALL RELATED FUNCTION   |****---------------------
---------------------******************************--------------------------

-- FREESWITCH API
fsapi = freeswitch.API()

---------------------------------------------------------------------------------------------------------------------------------------------

function detail_intcon(name, direction)
    return jsonhash(rdbconn:hgetall(intconkey(name, direction)))
end

function is_intcon_enable(name, direction)
    return fieldjsonify(rdbconn:hget(intconkey(name, direction), 'enable'))
end

---------------------------------------------------------------------------------------------------------------------------------------------
-- CONCURENT CALL
---------------------------------------------------------------------------------------------------------------------------------------------
function concurentcallskeys(name)
    local xvars = split(freeswitch.getGlobalVariable('CLUSTERMEMBERS'))
    for i=1, #xvars do
        xvars[i] = 'realtime:concurentcalls:'..name..':'..xvars[i]
    end
    return xvars
end

function get_defined_concurentcalls(name, direction)
    local class = rdbconn:hget(intconkey(name, direction), 'capacity_class')
    return fieldjsonify(rdbconn:hget('class:capacity:'..class, 'concurentcalls'))
end


function verify_concurentcalls(name, direction, uuid)
    local concurentcalls = 0
    local startpoint = 1
    local clustermembers = freeswitch.getGlobalVariable('CLUSTERMEMBERS')
    local cckeys = concurentcallskeys(name)
    local max_concurentcalls = get_defined_concurentcalls(name, direction)
    -- unlimited/bypass cps check
    if max_concurentcalls < 0 then
        return -math.huge, -1
    end
    if direction == INBOUND then startpoint = 2 end
    local replies = rdbconn:transaction({watch=cckeys, cas=true, retry=0}, function(txn)
        txn:multi()
        if direction == INBOUND then txn:sadd(concurentcallskey(name), uuid) end
        for i=1, #cckeys do txn:scard(cckeys) end
    end)
    for i=startpoint, #replies do concurentcalls = concurentcalls + tonumber(replies[i]) end
    return concurentcalls, max_concurentcalls
end

---------------------------------------------------------------------------------------------------------------------------------------------
-- CALL PER SECOND
---------------------------------------------------------------------------------------------------------------------------------------------

function get_defined_cps(name, direction)
    local class = rdbconn:hget(intconkey(name, direction), 'capacity_class')
    return fieldjsonify(rdbconn:hget('class:capacity:'..class, 'cps'))
end


function average_cps(name, direction)
    -- LEAKY BUCKET: https://en.wikipedia.org/wiki/Leaky_bucket
    -- shaping traffic with contant rate, eg: 10cps mean call every 100ms
    local leakybucket =[[
    local bucket = KEYS[1]
    local leakyms = tonumber(ARGV[1])
    local timestamp = redis.call('TIME')
    local current = math.ceil(1000*timestamp[1] + timestamp[2]/1000)
    local nextcall = current
    local lastcall = redis.call('GET', bucket)
    if lastcall then
        nextcall = math.max(tonumber(lastcall) + leakyms, current)
    end
    nextcall = math.max(nextcall, current)
    redis.call('PSETEX', bucket, nextcall-current+leakyms, nextcall)
    return {nextcall, current}
    ]]
    local bucket = 'realtime:leaky:bucket:'..name
    local max_cps = get_defined_cps(name, direction)
    local leakyms = math.ceil(1000/max_cps)
    -- unlimited/bypass cps check
    if max_cps < 0 then
        return 0, -math.huge, -1, leakyms, 0, 0
    end
    local timers = rdbconn:eval(leakybucket, 1, bucket, leakyms)
    local nextcall, current = timers[1], timers[2]
    local waitms = nextcall - current
    local queue = math.ceil((nextcall-current)/leakyms)
    return waitms, queue, max_cps, leakyms, current, nextcall
end


function verify_cps(name, direction, uuid)
    local violate_key = 'realtime:cps:violation:'..name
    local bucket = 'realtime:token:bucket:'..name
    local timestamp = math.floor(1000 * socket.gettime())                                       -- time stamp in ms; same as unit of ROLLING_WINDOW_TIME
    -- check if interconnection is blocked, use PTTL O(1) instead of EXISTS O(1):
    -- -2 if the key does not exist, -1 if the key exists but has no associated expire, +n milisecond if any
    local current_blocking_time = rdbconn:pttl(violate_key)
    -- mean this traffic is blocked
    if 0 < current_blocking_time then
        -- the call already blocked with VIOLATED_BLOCK=60000ms and ROLLING_WINDOW=1000ms
        if current_blocking_time < VIOLATED_BLOCK_TIME then
            rdbconn:psetex(violate_key, 3*VIOLATED_BLOCK_TIME, timestamp)
        end
        return false, nil, nil, current_blocking_time
    else
        local max_cps = get_defined_cps(name, direction)
        -- unlimited/bypass cps check
        if max_cps < 0 then
            return true, -math.huge, -1, 0
        end
        -- TOKEN BUCKET: https://en.wikipedia.org/wiki/Token_bucket
        -- eg: 10cps mean 10 call as last 1000ms and not 10 call at 999ms and next 10 calls more at 1001
        local tokenbucket = rdbconn:transaction(function(txn)
            txn:zremrangebyscore(bucket, '-inf', timestamp - ROLLING_WINDOW_TIME)               -- rotare the the set by remove the member that older
            txn:zadd(bucket, timestamp, uuid)                                                   -- add this request to history
            txn:zcard(bucket)                                                                   -- can use ZCARD to get number of member in the set p:zrange(history_key, 0, -1, 'withscores')
            txn:pexpire(bucket, 2*ROLLING_WINDOW_TIME)                                          -- auto remove the key if no request in milisecond, can just be ROLLING_WINDOW_TIME
        end)
        -- verification process
        local current_cps = tonumber(tokenbucket[3])
        -- rise up the blocking key
        if current_cps > max_cps then
            rdbconn:psetex(violate_key, VIOLATED_BLOCK_TIME, timestamp)
            return false, current_cps , max_cps, VIOLATED_BLOCK_TIME
        else
            return true, current_cps , max_cps, nil
        end
    end
end

---------------------------------------------------------------------------------------------------------------------------------------------
-- MEDIA
---------------------------------------------------------------------------------------------------------------------------------------------

function inMediaProcess(name, DxLeg)
    local class = rdbconn:hget(intconkey(name, INBOUND), 'media_class')
    local medias = jsonhash(rdbconn:hgetall('class:media:'..class))
    DxLeg:setVariable("codec_string", join(medias.codecs))
    DxLeg:setVariable("rtp_codec_negotiation", medias.codec_negotiation)
    DxLeg:setVariable("dtmf_type", medias.dtmf_mode)

    if medias.media_mode == 'bypass' then
        DxLeg:setVariable("bypass_media", "true")
    elseif medias.media_mode == 'proxy' then
        DxLeg:setVariable("proxy_media", "true")
    else end

    if medias.cng then
        DxLeg:setVariable("send_silence_when_idle", "true")
    else DxLeg:setVariable("suppress_cng", "true") end

    if medias.vad then
        DxLeg:setVariable("rtp_enable_vad_in", "true")
    else
        DxLeg:setVariable("rtp_disable_vad_in", "true")
    end
end

function outMediaProcess(name, DxLeg)
    local class = rdbconn:hget(intconkey(name, OUTBOUND), 'media_class')
    local medias = jsonhash(rdbconn:hgetall('class:media:'..class))

    DxLeg:execute("export", "nolocal:absolute_codec_string="..join(medias.codecs))
    DxLeg:execute("export", "nolocal:rtp_codec_negotiation="..medias.codec_negotiation)
    DxLeg:execute("export", "nolocal:dtmf_type="..medias.dtmf_mode)

    if medias.media_mode == 'bypass' then
        DxLeg:execute("export", "nolocal:bypass_media=true")
    elseif medias.media_mode == 'proxy' then
        DxLeg:execute("export", "nolocal:proxy_media=true")
    else end

    if medias.cng then
        DxLeg:execute("export", "nolocal:bridge_generate_comfort_noise=true")
    else DxLeg:execute("export", "nolocal:suppress_cng=true") end

    if medias.vad then
        DxLeg:execute("export", "nolocal:rtp_enable_vad_out=true")
    else
        DxLeg:execute("export", "nolocal:rtp_disable_vad_out=true")
    end
end

---------------------------------------------------------------------------------------------------------------------------------------------
-- get siprofile of interconnection name
function get_sipprofile(name, direction)
    return rdbconn:hget(intconkey(name, direction), 'sipprofile')
end

---------------------------------------------------------------------------------------------------------------------------------------------
-- early media processing
---------------------------------------------------------------------------------------------------------------------------------------------
function earlyMediaProcess(name, DxLeg)
    local class = rdbconn:hget(intconkey(name, INBOUND), 'preanswer_class')
    local streams = {}
    if class then streams = fieldjsonify(rdbconn:hget('class:preanswer:'..class, 'streams')) end
    for i=1, #streams do
        local streamtype = streams[i].type
        local streamdata = streams[i].stream
        if streamtype == 'tone' then
            DxLeg:execute('gentones', streamdata)
        elseif streamtype == 'media' then
            DxLeg:execute('playback', streamdata)
        elseif streamtype == 'speak' then
            DxLeg:execute('speak', 'flite|slt|'..streamdata)
        elseif streamtype == 'signal' then
            if ismeberof({'true', 'false', 'ring_ready'}, streamdata) then
                DxLeg:setVariable("ignore_early_media", streamdata)
            end
        else end
    end
end

---------------------------------------------------------------------------------------------------------------------------------------------
-- privacy and caller id type
---------------------------------------------------------------------------------------------------------------------------------------------
function callerIdPrivacyProcess(name, DxLeg)
    -- caller id type
    local cid_type = rdbconn:hget(intconkey(name, OUTBOUND), 'cid_type')
    if cid_type == 'auto' then cid_type = DxLeg:getVariable("sip_cid_type") end
    if not cid_type then cid_type = 'none' end
    DxLeg:execute("export", "nolocal:sip_cid_type="..cid_type)
    -- privacy
    local privacys = {}
    local dbprivacy = fieldjsonify(rdbconn:hget(intconkey(name, OUTBOUND), 'privacy'))
    for i=1, #dbprivacy do
        if dbprivacy[i] == 'none' then
            arrayinsert(privacys, '')
        elseif dbprivacy[i] == 'auto' then
            if DxLeg:getVariable("privacy_hide_name") == 'true' then arrayinsert(privacys, 'hide_name') end
            if DxLeg:getVariable("privacy_hide_number") == 'true' then arrayinsert(privacys, 'hide_number') end
        elseif dbprivacy[i] == 'screen' then
            arrayinsert(privacys, 'screen')
        elseif dbprivacy[i] == 'name' then
            arrayinsert(privacys, 'hide_name')
        elseif dbprivacy[i] == 'number' then
            arrayinsert(privacys, 'hide_number')
        else end
    end
    if #privacys > 0 then  DxLeg:execute("export", "nolocal:origination_privacy="..join(privacys, '+')) end
    --
    return cid_type, privacys
end

---------------------------------------------------------------------------------------------------------------------------------------------
--- gateway connection param
function getgw(name)
    local proxy, _port, transport = unpack(rdbconn:hmget('base:gateway:'..name, {'proxy', 'port', 'transport'}))
    return proxy, tonumber(_port:sub(6,#_port)), transport
end
---------------------------------------------------------------------------------------------------------------------------------------------
-- TRANSLATION
---------------------------------------------------------------------------------------------------------------------------------------------
function get_translation_rules(name, direction)
    local classes = fieldjsonify(rdbconn:hget(intconkey(name, direction), 'translation_classes'))
    if #classes == 0 then
        return {}
    else
        local replies = rdbconn:pipeline(function(pipe)
            for _, class in pairs(classes) do
                pipe:hgetall('class:translation:'..class)
            end
        end)
        return replies
    end
end

function translate(clidnum, clidname, destnum, name, direction)
    local translated_clidnum = clidnum
    local translated_clidname = clidname
    local translated_destnum = destnum
    local match_rules = {}
    local rules = get_translation_rules(name, direction)
    for i=1, #rules do
        local caller_number_pattern = rules[i].caller_number_pattern
        local destination_number_pattern = rules[i].destination_number_pattern
        -- check condtion
        local condition = true
        if (#caller_number_pattern > 0) then
            condition = toboolean(fsapi:execute('regex', translated_clidnum..'|'..caller_number_pattern..'|'))
        end
        if (condition and (#destination_number_pattern > 0)) then
            condition = toboolean(fsapi:execute('regex', translated_destnum..'|'..destination_number_pattern..'|'))
        end
        -- translate only both conditions are true
        if condition then
            if (#caller_number_pattern > 0) then
                translated_clidnum = fsapi:execute('regex', translated_clidnum..'|'..caller_number_pattern..'|'..rules[i].caller_number_replacement)
            end
            if (#destination_number_pattern > 0) then
                translated_destnum = fsapi:execute('regex', translated_destnum..'|'..destination_number_pattern..'|'..rules[i].destination_number_replacement)
            end
            -- caler id name
            local caller_name = rules[i].caller_name
            if caller_name then
                if caller_name == '_caller_number' then
                    translated_clidname = translated_clidnum
                elseif caller_name == '_auto' then
                else
                    translated_clidname = caller_name
                end
            end
            arrayinsert( match_rules, rules[i].name)
        end
    end
    return translated_clidnum, translated_clidname, translated_destnum,  match_rules
end
---------------------------------------------------------------------------------------------------------------------------------------------
-- MANIPULATION
---------------------------------------------------------------------------------------------------------------------------------------------
function boolstr(str)
    if str == 'true' then
        return false
    else
        return true
    end
end


-- CHECK MANIPUALTION IF STATEMENTS OR CONDITIONS
function ifverify(conditions, DxLeg, NgVars)
    local positive = true
    if conditions then
        local logic = conditions.logic
        local rules = conditions.rules
        for i=1,#rules do
            -- get var
            local sublogic
            local pattern = rules[i].pattern
            local refervar = rules[i].refervar
            local refervalue = NgVars[refervar]
            if not refervalue then
                refervalue = DxLeg:getVariable(refervar)
            end
            -- condition check
            if refervalue then
                if pattern then
                    sublogic = boolstr(fsapi:execute('regex', refervalue..'|'..pattern))
                else
                    sublogic = true
                end
            else
                sublogic = false
            end
            -- logic break
            if logic == 'AND' then
                if sublogic == false then
                    return false
                end
            else
                if sublogic == true then
                    return true
                else
                    positive = false
                end
            end
        end
    end
    -- return if statement with bool value
    return positive
end


-- BUILD THE VALUES: TURN abstract-array --> fixed-array --> fixed-string
function turnvalues(values, refervar, pattern, DxLeg, NgVars)
    local replacements = {}
    for i=1,#values do
        local value = values[i]
        -- regex: backreferences and subexpressions
        if value:match('%%') then
            if refervar and pattern then
                local refervalue = NgVars[refervar]
                if not refervalue then
                    refervalue = DxLeg:getVariable(refervar)
                end
                if refervalue then
                    arrayinsert(replacements, fsapi:execute('regex', refervalue..'|'..pattern..'|'..value))
                end
            else
                arrayinsert(replacements, value)
            end
        -- get from ngvars / channel var / fixed str
        else
            local repl = NgVars[value]
            if repl then
                arrayinsert(replacements, repl)
            else
                repl = DxLeg:getVariable(value)
                if repl then
                    arrayinsert(replacements, repl)
                else
                    arrayinsert(replacements, value)
                end
            end
        end
    end
    -- concat
    return table.concat(replacements)
end

-------------------------------------------------------------------------------
-- INBOUND NORMALIZE
-------------------------------------------------------------------------------
function normalize(DxLeg, NgVars)
    local classes = fieldjsonify(rdbconn:hget(intconkey(NgVars.intconname, INBOUND), 'manipulation_classes'))
    for i=1,#classes do
        local manipulations = jsonhash(rdbconn:hgetall('class:manipulation:'..classes[i]))
        local conditions = manipulations.conditions
        -- check the condition
        local positive = ifverify(conditions, DxLeg)
        -- run action
        local maniactions = manipulations.actions
        if positive == false then
            maniactions = manipulations.antiactions
        end
        for j=1,#maniactions do
            local action = maniactions[j].action
            local refervar = maniactions[j].refervar
            local pattern = maniactions[j].pattern
            local targetvar = maniactions[j].targetvar
            local values = maniactions[j].values
            -- action process
            if action == 'set' then
                local valuestr = turnvalues(values, refervar, pattern, DxLeg, NgVars)
                if #valuestr==0 then
                    NgVars[targetvar] = nil
                    DxLeg:execute('unset', targetvar)
                else
                    if startswith(targetvar, 'ng') or NgVars[targetvar] then
                        NgVars[targetvar] = valuestr
                    else
                        DxLeg:setVariable(targetvar, valuestr)
                    end
                end
            elseif action == 'log' then
                local valuestr = turnvalues(values, refervar, pattern, DxLeg, NgVars)
                log.info('module=callng, space=callfunc, action=normalize, seshid=%s, log=%s', NgVars.seshid, valuestr)
            elseif action == 'hangup' then
                NgVars.LIBRE_HANGUP_CAUSE = values[1]
                DxLeg.hangup()
            else
                DxLeg:sleep(tonumber(values[1]))
            end
        end
    end
end

-------------------------------------------------------------------------------
-- OUTBOUND MANIPULATION
-------------------------------------------------------------------------------
function manipulate(DxLeg, NgVars)
    local classes = fieldjsonify(rdbconn:hget(intconkey(NgVars.route, OUTBOUND), 'manipulation_classes'))
    for i=1,#classes do
        local manipulations = jsonhash(rdbconn:hgetall('class:manipulation:'..classes[i]))
        local conditions = manipulations.conditions
        -- check the condition
        local positive = ifverify(conditions)
        -- run action
        local maniactions = manipulations.actions
        if positive == false then
            maniactions = manipulations.antiactions
        end
        for j=1,#maniactions do
            local action = maniactions[j].action
            local refervar = maniactions[j].refervar
            local pattern = maniactions[j].pattern
            local targetvar = maniactions[j].targetvar
            local values = maniactions[j].values
            -- action process
            if action == 'set' then
                local valuestr = turnvalues(values, refervar, pattern, DxLeg, NgVars)
                if #valuestr==0 then
                    NgVars[targetvar] = nil
                    DxLeg:execute('unset', targetvar)
                else
                    if startswith(targetvar, 'ng') or NgVars[targetvar] then
                        NgVars[targetvar] = valuestr
                    else
                        DxLeg:execute('export', 'nolocal:'..targetvar..'='..valuestr)
                    end
                end
            elseif action == 'log' then
                local valuestr = turnvalues(values, refervar, pattern, DxLeg, NgVars)
                log.info('module=callng, space=callfunc, action=manipulate, seshid=%s, log=%s', NgVars.seshid, valuestr)
            elseif action == 'hangup' then
                NgVars.LIBRE_HANGUP_CAUSE = values[1]
                DxLeg.hangup()
            else
                DxLeg:sleep(tonumber(values[1]))
            end
        end
    end
end
---------------------------------------------------------------------------------------------------------------------------------------------
-- ROUTING
---------------------------------------------------------------------------------------------------------------------------------------------
function pchoice(a, b, p)
    local x = random(100)
    if x < p then return a, b
    else return b, a end
end

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

local function curlroute(url, query)
    local p, s
    local ok, err, body, status = curlget( url..'?'..query, {["x-nodeid"] = NODEID})
    if not ok or status~=200 then
        log.error('module=callng, space=callfunc, action=curlroute, url=%s, query=%s, error=%s', url, query, err)
    else
        p, s = unpack(json.decode(body))
    end
    return p, s
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

local function httproute(url, query)
    local p, s
    local res, code, _, _, body = httprequest("GET", url..'?'..query, nil, {["x-nodeid"] = NODEID})
    if res==nil or code~=200 then
        log.error('module=callng, space=callfunc, action=httproute, url=%s, query=%s, error=%s', url, query, code)
    else
        p, s = unpack(json.decode(table.concat(body)))
    end
    return p, s
end

---------------------------------------------------------------------------------------------------------------------------------------------

function routing_query(tablename, routingdata)
    local routingrules = {}
    local primary, secondary, load
    ---
    repeat
        -- routing table process
        local routevalue = nil
        local schema = jsonhash(rdbconn:hgetall('routing:table:'..tablename))
        -- return immediately if invalid schema
        if (not next(schema)) then return nil, nil, routingrules end
        arrayinsert(routingrules, tablename)
        local schema_action = schema.action
        if schema_action == BLOCK then
            return BLOCK, BLOCK, routingrules
        elseif schema_action == ROUTE then
            primary, secondary = pchoice(schema.routes[1], schema.routes[2], tonumber(schema.routes[3]))
            return primary, secondary, routingrules
        elseif schema_action == QUERY then
            local variable = schema.variables[1]
            local value = routingdata[variable]
            -- return immediately if invalid schema
            if (not value) then return nil, nil, routingrules end
            -- route lookup {eq, ne, gt, lt}
            local hashroute = rdbconn:hgetall('routing:record:'..tablename..':compare:')
            if next(hashroute) then
                for hfield, hvalue in pairs(hashroute) do
                    local compare, param = unpack(split(hfield, ':'))
                    local paramvalue = routingdata[param]
                    -- if not get dynamic value, use fixed value
                    if not paramvalue then paramvalue = param end
                    if compare=='eq' then
                        if value==paramvalue then
                            arrayinsert(routingrules, compare..'.'..param); routevalue = hvalue; break
                        end
                    elseif compare=='ne' then
                        if value~=paramvalue then
                            arrayinsert(routingrules, compare..'.'..param); routevalue = hvalue; break
                        end
                    elseif compare=='gt' then
                        if tonumber(paramvalue) and tonumber(value) and tonumber(value) > tonumber(paramvalue) then
                            arrayinsert(routingrules, compare..'.'..param); routevalue = hvalue; break
                        end
                    elseif compare=='lt' then
                        if tonumber(paramvalue) and tonumber(value) and tonumber(value) < tonumber(paramvalue) then
                            arrayinsert(routingrules, compare..'.'..param); routevalue = hvalue; break
                        end
                    else end
                end
            end
            --route lookup {em, lpm}
            if not routevalue then
                routevalue = rdbconn:get('routing:record:'..tablename..':em:'..value)
                if routevalue then
                    arrayinsert(routingrules, 'em.'..value)
                else
                    for i=0, #value do
                        local prefix = value:sub(1,#value-i)
                        routevalue = rdbconn:get('routing:record:'..tablename..':lpm:'..prefix)
                        if routevalue then
                            arrayinsert(routingrules, 'lpm.'..prefix)
                            break
                        end
                    end
                end
            end
        elseif schema_action == HTTPR then
            local variables = schema.variables
            local params = {}
            for i=1, #variables do
                local variable = variables[i]
                arrayinsert(params, variable..'='..routingdata[variable])
            end
            local query = join(params, '&')
            primary, secondary = curlroute(schema.routes, query)
            return primary, secondary, {'routing.via.http'}
        else
            return nil, nil, routingrules
        end
        -- routing record process
        if routevalue then
            local action, p, s, l = unpack(split(routevalue, ':'))
            if action == BLOCK then
                return BLOCK, BLOCK, routingrules
            elseif action == JUMPS then
                tablename, _ = pchoice(p, s, tonumber(l))
                goto REQUERYROUTE
            elseif action == ROUTE then
                primary, secondary = pchoice(p, s, tonumber(l))
                return primary, secondary, routingrules
            else
                return nil, nil, routingrules
            end
        end
        ::REQUERYROUTE::
    until (ismeberof(routingrules, tablename) or (#routingrules >= 10) or (primary))
    return primary, secondary, routingrules
end

---------------------------------------------------------------------------------------------------------------------------------------------
-- DISTRIBUTION
---------------------------------------------------------------------------------------------------------------------------------------------
function get_distribution_algorithm(name)
    return fieldjsonify(rdbconn:hget(intconkey(name, OUTBOUND), 'distribution'))
end

function hashchoicegw(name, _sipprofile, field)
    local allgws = rdbconn:hkeys(intconkey(name, OUTBOUND)..':_gateways')
    local downgws = split(fsapi:executeString('sofia profile '.._sipprofile..' gwlist down'), __space__)
    local upgws = arraycomplement(allgws, downgws)
    table.sort(upgws)
    local hnumber =  tonumber(string.sub(fsapi:executeString('md5 '..field),12,20),32)
    if #upgws > 0 then
        return upgws[1+hnumber-math.floor(hnumber/#upgws)*#upgws]
    else
        return '-err'
    end
end

