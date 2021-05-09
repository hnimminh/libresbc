
---------------------******************************--------------------------
---------------------****|  RDB & MORE  FUNCTION   |****---------------------
---------------------******************************--------------------------
function intconkey(name, direction)
    if direction == INBOUND then
        return 'intcon:in:'..name
    else
        return 'intcon:out:'..name
    end 
end

function detail_intcon(name, direction)
    return jsonhash(rdbconn:hgetall(intconkey(name, direction)))
end


function is_intcon_enable(name, direction)
    return fieldjsonify(rdbconn:hget(intconkey(name, direction), 'enable'))
end


---------------------------------------------------------------------------------------------------------------------------------------------
-- CONCURENT CALL 
---------------------------------------------------------------------------------------------------------------------------------------------
function concurentcallskey(name, node)
    if not node then node = NODEID end
    return 'realtime:concurentcalls:'..name..':'..node
end

function concurentcallskeys(name)
    local clustermembers = split(freeswitch.getGlobalVariable('CLUSTERMEMBERS'))
    local _concurentcallskeys = {}
    for i=1, #clustermembers do
        table.insert( _concurentcallskeys, concurentcallskey(name, clustermembers[i]))
    end
    return _concurentcallskeys
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
        txn:sadd(concurentcallskey(name), uuid)
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

---------------------------------------------------------------------------------------------------------------------------------------------
-- TRANSLATION 
---------------------------------------------------------------------------------------------------------------------------------------------


---------------------------------------------------------------------------------------------------------------------------------------------
-- MANIPULATION 
---------------------------------------------------------------------------------------------------------------------------------------------


---------------------------------------------------------------------------------------------------------------------------------------------
-- ROUTING 
---------------------------------------------------------------------------------------------------------------------------------------------

