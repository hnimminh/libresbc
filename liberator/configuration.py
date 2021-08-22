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
_SWVERSION = '0.5.5'
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
SWCODECS = ['ALAW', 'ULAW', 'OPUS', 'G729', 'AMR', 'AMR-WB']
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
CHANGE_CFG_CHANNEL = 'CHANGE_CFG_CHANNEL'
SECURITY_CHANNEL = 'SECURITY_CHANNEL'
#-----------------------------------------------------------------------------------------------------
# CALL ENGINE EVENT SOCKET
#-----------------------------------------------------------------------------------------------------
ESL_HOST = '127.0.0.1'
ESL_PORT = 8021

# LOG DIRECTORY
LOGDIR = '/var/log/libresbc'

#-----------------------------------------------------------------------------------------------------
# HTTPCDR DATA
#-----------------------------------------------------------------------------------------------------
HTTPCDR_ENDPOINTS = {{httpcdr.endpoints if httpcdr else 'None'}}
