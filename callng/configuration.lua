--
-- callng:configuration.lua
-- 
-- The Initial Developer of the Original Code is
-- Minh Minh <hnimminh at[@] outlook dot[.] com>
-- Portions created by the Initial Developer are Copyright (C) the Initial Developer. 
-- All Rights Reserved.
--

-- configuration
SWVERSION = '{{version}}'
NODEID = '{{nodeid}}'

--- REDIS ENDPOINT
REDIS_HOST = '{{redis.host}}'
REDIS_PORT = {{redis.port}}
REDIS_DB = {{redis.database}}
REDIS_PASSWORD = {{('%s')|format(redis.password)|to_json if redis.password else 'nil'}}
SCAN_COUNT = 1000
REDIS_TIMEOUT = 5

---  CONSTANT
INBOUND = 'inbound'
OUTBOUND = 'outbound'

--- ROUTING ACTION
QUERY = 'query'
BLOCK = 'block'
JUMPS = 'jumps'
ROUTE = 'route'
EMPTYSTRING = ''
--- CDR 
CDRTTL = 3600

--- SECURITY
ROLLING_WINDOW_TIME = 1000                             --- use the exactly 1 second = 1000ms
VIOLATED_BLOCK_TIME = 60*ROLLING_WINDOW_TIME           --- if violate block 60000ms, it can be increase if violate;

SRPT_ENCRYPTION_SUITES = {'AES_CM_128_HMAC_SHA1_80', 'AES_CM_128_HMAC_SHA1_32'}

--- LOG DIRECTORY
LOGDIR = '{{logdir}}'
