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
_DESCRIPTION = 'Open Source Session Border Controller for Large-Scale Voice Infrastructures'
_SWVERSION = '0.5.10-b'
#-----------------------------------------------------------------------------------------------------
# LIBRE
#-----------------------------------------------------------------------------------------------------
LOGDIR = '/var/log/libresbc'
ETCDIR = '/etc/libresbc'
RUNDIR = '/run/libresbc'
#-----------------------------------------------------------------------------------------------------
# RBD UNIX SOCKET LOCALIZE INSTANCE
#-----------------------------------------------------------------------------------------------------
RDB_PIDFILE = f'{RUNDIR}/redis.pid'
RDB_USOCKET = f'{RUNDIR}/redis.sock'

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
_BUILTIN_ACLS_ = ['rfc1918.auto', 'nat.auto', 'localnet.auto', 'loopback.auto', 'none']
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
NODEID_CHANNEL = f'{NODEID.upper()}_CHANNEL'
#-----------------------------------------------------------------------------------------------------
# CALL ENGINE EVENT SOCKET
#-----------------------------------------------------------------------------------------------------
ESL_HOST = '127.0.0.1'
ESL_PORT = 8021

#-----------------------------------------------------------------------------------------------------
# HTTPCDR DATA
#-----------------------------------------------------------------------------------------------------
HTTPCDR_ENDPOINTS = {{httpcdr.endpoints if httpcdr else 'None'}}
DISKCDR_ENABLE = {% if diskcdr is defined %}{{ 'True' if diskcdr else 'False'}}{% else %}False{% endif %}
