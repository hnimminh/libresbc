-- configuration
_SWVERSION = '{{version}}'
NODEID = '{{nodeid}}'

--- REDIS ENDPOINT
REDIS_HOST = '{{redis.host}}'
REDIS_PORT = {{redis.port}}
REDIS_DB = {{redis.database}}
REDIS_PASSWORD = {{('%s')|format(redis.password)|to_json if redis.password else 'nil'}}
SCAN_COUNT = 1000
RACTION_TIMEOUT = 5

--- SECURITY
_ROLLING_WINDOW_TIME = 1000                              --- use the exactly 1 second = 1000ms
_VIOLATED_BLOCK_TIME = 60*_ROLLING_WINDOW_TIME           --- if violate block 60000ms, it can be increase if violate;

--- LOG
LOGDIR = '{{logdir}}'

SRPT_ENCRYPTION_SUITES = {'AES_CM_128_HMAC_SHA1_80', 'AES_CM_128_HMAC_SHA1_32'}
