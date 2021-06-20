#
# liberator:configuration.py
# 
# The Initial Developer of the Original Code is
# Minh Minh <hnimminh at[@] outlook dot[.] com>
# Portions created by the Initial Developer are Copyright (C) the Initial Developer. 
# All Rights Reserved.
#

#-----------------------------------------------------------------------------------------------------
#      GLOBAL CONFIGURATION FILES
#-----------------------------------------------------------------------------------------------------
_APPLICATION = 'LIBRESBC'
_SWVERSION = '{{version}}'
_DESCRIPTION = 'Open Source Session Border Controller for Large-Scale Voice Infrastructures'
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
SWCODECS = ['ALAW', 'ULAW', 'OPUS', 'G729']
_BUILTIN_ACLS_ = ['rfc1918.auto', 'nat.auto', 'localnet.auto', 'loopback.auto']
#-----------------------------------------------------------------------------------------------------
# SERVER PROPERTIES
#-----------------------------------------------------------------------------------------------------
NODEID = '{{nodeid}}'
CLUSTERS = {
    'name': 'defaultname',
    'members': [NODEID],
    "rtp_start_port": 0,
    "rtp_end_port": 0,
    "max_calls_per_second": 0,
    "max_concurrent_calls": 0
}
#-----------------------------------------------------------------------------------------------------
# CALL ENGINE EVENT SOCKET
#-----------------------------------------------------------------------------------------------------
ESL_HOST = '127.0.0.1'
ESL_PORT = 8021
ESL_SECRET = '{{callengine.secret}}'
# DEFAULT SIP SECRET
DEFAULT_PASSWORD = '{{callengine.sipsecret}}'

# LOG DIRECTORY
LOGDIR = '{{logdir}}'

#-----------------------------------------------------------------------------------------------------
# HTTPCDR DATA
#-----------------------------------------------------------------------------------------------------
HTTPCDR_ENDPOINTS = {{httpcdr.endpoints if httpcdr else 'None'}}