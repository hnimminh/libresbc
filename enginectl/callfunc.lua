dofile("{{rundir}}/enginectl/utilities.lua")
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

-- LEAKY BUCKET: https://en.wikipedia.org/wiki/Leaky_bucket
function leaky_bucket(bucket, cps)
    timestamp = math.floor(1000 * socket.gettime())
    earliest = timestamp - ROLLING_WINDOW_TIME
    constantrate = ROLLING_WINDOW_TIME/cps

    atomicity = [[
    local bucket = KEYS[1]
    local thistime  = tonumber(ARGV[1])
    local nexttime = thistime

    redis.call('ZREMRANGEBYSCORE', bucket, '-inf', tonumber(ARGV[2]))
    local last = redis.call('ZRANGE', bucket, -1, -1)
    if #last > 0 then nexttime = tonumber(last[1]) + tonumber(ARGV[3]) end

    if thistime > nexttime then nexttime = thistime end
    redis.call('ZADD', bucket, nexttime, nexttime)

    return nexttime - thistime
    ]]

    return rdbconn:eval(atomicity, 1, bucket, timestamp, earliest, constantrate)
end

-- TOKEN BUCKET: https://en.wikipedia.org/wiki/Token_bucket
function token_bucket(bucket, uuid, timestamp)
    return rdbconn:transaction(function(txn)
        txn:zremrangebyscore(bucket, '-inf', timestamp - ROLLING_WINDOW_TIME)          -- rotare the the set by remove the member that older
        txn:zadd(bucket, timestamp, uuid)                                              -- add this request to history
        txn:zcard(bucket)                                                              -- can use ZCARD to get number of member in the set p:zrange(history_key, 0, -1, 'withscores')
        txn:pexpire(bucket, 3*ROLLING_WINDOW_TIME)                                     -- auto remove the key if no request in milisecond, can just be _ROLLING_WINDOW_TIME
    end)
end

function verify_cps(name, direction, uuid)
    -- eg: 10cps mean 10 call as last 1 second, edge case covered disallow 10 call at x.999 ms and next 10 calls more at (x+1).001
    local violate_key = 'call:cps:violation:'..name
    local history_key = 'call:cps:history:'..name
    local timestamp = math.floor(1000 * socket.gettime())                                       -- time stamp in ms; same as unit of ROLLING_WINDOW_TIME
    -- check if interconnection is blocked
    -- use PTTL O(1) instead of EXISTS O(1): -2 if the key does not exist, -1 if the key exists but has no associated expire, +n milisecond if any
    local current_blocking_time = rdbconn:pttl(violate_key)
    -- mean this traffic is blocked
    if 0 < current_blocking_time then
        -- below block is a optimization, you can comeback once you understand the rest of code.
        -- the call already blocked with VIOLATED_BLOCK=60000 ms and ROLLING_WINDOW=1000ms
        -- you just need to update from 59,000 to current timepoint; the update is useless for ealier
        -- if current_blocking_time < ROLLING_WINDOW_TIME then token_bucket() end
        -- increase by triple violated blocking time
        rdbconn:psetex(violate_key, 2*VIOLATED_BLOCK_TIME, timestamp)
        -- return
        return false, nil, nil, current_blocking_time
    else
        local replies = token_bucket(history_key, uuid, timestamp)
        -- verification process
        local current_cps = tonumber(replies[3])
        local max_cps = get_defined_cps(name, direction)
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
-- CODEC 
---------------------------------------------------------------------------------------------------------------------------------------------
function get_codec(name, direction)
    local class = rdbconn:hget(intconkey(name, direction), 'codec_class')
    return join(fieldjsonify(rdbconn:hget('class:codec:'..class, 'codecs')))
end

-- get siprofile of interconnection name
function get_sipprofile(name, direction)
    return rdbconn:hget(intconkey(name, direction), 'sipprofile')
end

---------------------------------------------------------------------------------------------------------------------------------------------
-- TRANSLATION 
---------------------------------------------------------------------------------------------------------------------------------------------
function get_translation_rules(name, direction)
    local classes = rdbconn:hget(intconkey(name, direction), 'translation_classes')
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

function translate(caller, callee, name, direction)
    local translated_caller = caller
    local translated_callee = callee
    local match_rules = {}
    local rules = get_translation_rules(name, direction)
    for i=1, #rules do
        local caller_pattern = rules[i].caller_pattern
        local callee_pattern = rules[i].callee_pattern
        -- check condtion
        local condition = true
        if (#caller_pattern > 0) then
            condition = toboolean(fsapi:execute('regex', translated_caller..'|'..caller_pattern..'|'))
        end
        if (condition and (#callee_pattern > 0)) then 
            condition = toboolean(fsapi:execute('regex', translated_callee..'|'..callee_pattern..'|'))
        end
        -- translate only both conditions are true
        if condition then
            if (#caller_pattern > 0) then
                translated_caller = fsapi:execute('regex', caller..'|'..caller_pattern..'|'..rules[i].caller_replacement)
            end
            if (#callee_pattern > 0) then
                translated_callee = fsapi:execute('regex', caller..'|'..callee_pattern..'|'..rules[i].callee_replacement)
            end
            arrayinsert( match_rules, rules[i].name)
        end
    end
    return translated_caller, translated_callee, match_rules
end
---------------------------------------------------------------------------------------------------------------------------------------------
-- MANIPULATION 
---------------------------------------------------------------------------------------------------------------------------------------------


---------------------------------------------------------------------------------------------------------------------------------------------
-- ROUTING 
---------------------------------------------------------------------------------------------------------------------------------------------
function pchoice(a, b, p)
    local x = random(100)
    if x < p then return a, b
    else return b, a end
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
            routevalue = rdbconn:hgetall('routing:record:'..tablename..':em:'..value)
            if next(routevalue) then
                arrayinsert(routingrules, 'em-'..value)
            else
                for i=0, #value do
                    local prefix = value:sub(1,#value-i)
                    routevalue = rdbconn:hgetall('routing:record:'..tablename..':lpm:'..prefix)
                    if next(routevalue) then
                        arrayinsert(routingrules, 'lpm-'..prefix)
                        break
                    end
                end
            end
        else
            return nil, nil, routingrules
        end
        -- routing record process
        if routevalue then
            action = routevalue.action
            if action == BLOCK then
                return BLOCK, BLOCK, routingrules
            elseif action == QUERY then
                tablename, _ = pchoice(routevalue.routes[1], routevalue.routes[2], tonumber(routevalue.routes[3]))
                goto REQUERYROUTE
            elseif action == ROUTE then
                primary, secondary = pchoice(routevalue.routes[1], routevalue.routes[2], tonumber(routevalue.routes[3]))
                return primary, secondary, routingrules
            else
                return nil, nil, routingrules
            end
        end
        ::REQUERYROUTE::
    until (ismeberof(routingrules, tablename) or (#routingrules >= 10) or (primary))
    return primary, secondary, routingrules
end

