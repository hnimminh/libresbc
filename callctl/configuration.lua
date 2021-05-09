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
CDR_TTL = 3600

--- SECURITY
ROLLING_WINDOW_TIME = 1000                             --- use the exactly 1 second = 1000ms
VIOLATED_BLOCK_TIME = 60*ROLLING_WINDOW_TIME           --- if violate block 60000ms, it can be increase if violate;

--- LOG
LOGDIR = '{{logdir}}'

SRPT_ENCRYPTION_SUITES = {'AES_CM_128_HMAC_SHA1_80', 'AES_CM_128_HMAC_SHA1_32'}
