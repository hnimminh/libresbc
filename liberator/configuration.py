#--------------------------------------------------------------------------------
#      GLOBAL CONFIGURATION FILES
#--------------------------------------------------------------------------------
_APPLICATION = 'LIBRESBC'
_SWVERSION = '{{version}}'
_DESCRIPTION = 'freedomland of yourvoip'

# REDIS ENDPOINT
REDIS_HOST = '{{redis.host}}'
REDIS_PORT = {{redis.port}}
REDIS_DB = {{redis.database}}
REDIS_PASSWORD = {{ ('%s')|format(redis.password)|to_json if redis.password else 'None' }}
SCAN_COUNT = 1000
RACTION_TIMEOUT = 5

# VOICE ATTRIBUTE
SWCODECS = ['ALAW', 'ULAW', 'G729']
MAX_CPS = 200
MAX_ACTIVE_SESSION = 60000

# SERVER PROPERTIES
_DEFAULT_NODENAME = 'LIBRE-DEFAULT-NODENAME'
_DEFAULT_CLUSTERNAME = 'LIBRE-DEFAULT-CLUSTERNAME'
#
NODEID = '{NODEID}'
NODENAME = DEFAULT_NODENAME
CLUSTERNAME = DEFAULT_CLUSTERNAME
CLUSTERMEMBERS = [NODEID]
