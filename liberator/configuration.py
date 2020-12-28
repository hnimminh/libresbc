#-----------------------------------------------------------------------------------------------------
#      GLOBAL CONFIGURATION FILES
#-----------------------------------------------------------------------------------------------------
_APPLICATION = 'LIBRESBC'
_SWVERSION = '{{version}}'
_DESCRIPTION = 'Freedom Land For Your Voice Infrastructures'
#-----------------------------------------------------------------------------------------------------
# REDIS ENDPOINT
#-----------------------------------------------------------------------------------------------------
REDIS_HOST = '{{redis.host}}'
REDIS_PORT = {{redis.port}}
REDIS_DB = {{redis.database}}
REDIS_PASSWORD = {{ ('%s')|format(redis.password)|to_json if redis.password else 'None' }}
SCAN_COUNT = 1000
REDIS_TIMEOUT = 5
#-----------------------------------------------------------------------------------------------------
# VOICE ATTRIBUTE
#-----------------------------------------------------------------------------------------------------
SWCODECS = ['ALAW', 'ULAW', 'G729']
MAX_CPS = 200
MAX_ACTIVE_SESSION = 60000
#-----------------------------------------------------------------------------------------------------
# SERVER PROPERTIES
#-----------------------------------------------------------------------------------------------------
_DEFAULT_NODENAME = 'LIBRE-DEFAULT-NODENAME'
_DEFAULT_CLUSTERNAME = 'LIBRE-DEFAULT-CLUSTERNAME'
#-----------------------------------------------------------------------------------------------------
NODEID = '{{nodeid}}'
NODENAME = _DEFAULT_NODENAME
CLUSTERNAME = _DEFAULT_CLUSTERNAME
CLUSTERMEMBERS = [NODEID]
#-----------------------------------------------------------------------------------------------------
# CALL ENGINE
#-----------------------------------------------------------------------------------------------------
CES_HOST = '{{callengine.socket.host}}'
CES_PORT = {{callengine.socket.port}}
CES_USER = '{{callengine.socket.user}}'
CES_SECRET = '{{callengine.socket.secret}}'
