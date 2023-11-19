--
-- callng:configuration.lua
--
-- The Initial Developer of the Original Code is
-- Minh Minh <hnimminh at[@] outlook dot[.] com>
-- Portions created by the Initial Developer are Copyright (C) the Initial Developer.
-- All Rights Reserved.
--

-- configuration
NODEID = os.getenv("NODEID")
if not NODEID then
    os.exit()
end

--- REDIS ENDPOINT
REDIS_HOST = os.getenv("REDIS_HOST")
if not REDIS_HOST then REDIS_HOST = "127.0.0.1" end

REDIS_PORT = os.getenv("REDIS_PORT")
if not REDIS_PORT then REDIS_PORT = 6379 end

REDIS_DB = os.getenv("REDIS_DB")
if not REDIS_DB then REDIS_DB = 0 end

REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
if not REDIS_PASSWORD then REDIS_PASSWORD = nil end

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

--- LOG SETTINGS
LOGDIR              = '/var/log/libresbc'
LOGLEVEL            = (os.getenv('LOGLEVEL') or 'INFO'):upper()
LOGSTACKS           = (os.getenv('LOGSTACKS') or EMPTYSTRING):upper()
LOGSTACK_CONSOLE    = string.find(LOGSTACKS, 'CONSOLE')
LOGSTACK_FILE       = string.find(LOGSTACKS, 'FILE') and LOGDIR..'/callng.log'
LOGSTACK_SYSLOG     = string.find(LOGSTACKS, 'SYSLOG')

-----------------------------------------------------------------------------------------------------
SECURITY_CHANNEL = 'SECURITY_CHANNEL'
