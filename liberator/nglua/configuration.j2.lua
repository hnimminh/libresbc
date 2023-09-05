--
-- callng:configuration.lua
--
-- The Initial Developer of the Original Code is
-- Minh Minh <hnimminh at[@] outlook dot[.] com>
-- Portions created by the Initial Developer are Copyright (C) the Initial Developer.
-- All Rights Reserved.
--

-- configuration
NODEID = '{{NODEID}}'

--- REDIS ENDPOINT
REDIS_HOST = '{{REDIS_HOST}}'
REDIS_PORT = {{REDIS_PORT}}
REDIS_DB = {{REDIS_DB}}
REDIS_PASSWORD = {{("'%s'")|format(REDIS_PASSWORD) if REDIS_PASSWORD else "nil"}}
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
HTTPR = 'httpr'
EMPTYSTRING = ''
--- CDR
CDRTTL = 3600

--- SECURITY
ROLLING_WINDOW_TIME = 1000                             --- use the exactly 1 second = 1000ms
VIOLATED_BLOCK_TIME = 60*ROLLING_WINDOW_TIME           --- if violate block 60000ms, it can be increase if violate;

SRPT_ENCRYPTION_SUITES = {'AES_CM_128_HMAC_SHA1_80', 'AES_CM_128_HMAC_SHA1_32'}

--- LOG DIRECTORY
LOGDIR = '/var/log/libresbc'

-----------------------------------------------------------------------------------------------------
SECURITY_CHANNEL = 'SECURITY_CHANNEL'
