#
# liberator:configuration.py
#
# The Initial Developer of the Original Code is
# Minh Minh <hnimminh at[@] outlook dot[.] com>
# Portions created by the Initial Developer are Copyright (C) the Initial Developer.
# All Rights Reserved.
#
import os
#-----------------------------------------------------------------------------------------------------
#      GLOBAL CONFIGURATION FILES
#-----------------------------------------------------------------------------------------------------
_APPLICATION = 'LIBRESBC'
_DESCRIPTION = 'Open Source Session Border Controller for Large-Scale Voice Infrastructures'
_SWVERSION = 'v1.0.0'
#-----------------------------------------------------------------------------------------------------
# LIBRE
#-----------------------------------------------------------------------------------------------------
LOGDIR = '/var/log/libresbc'
ETCDIR = '/etc/libresbc'
RUNDIR = '/run/libresbc'

#-----------------------------------------------------------------------------------------------------
# LOGGING
#-----------------------------------------------------------------------------------------------------
LOGLEVEL = 'INFO'
_LOGLEVEL = os.getenv('LOGLEVEL')
if _LOGLEVEL:
    LOGLEVEL = LOGLEVEL.upper()
    if LOGLEVEL not in ['DEBUG', 'INFO', 'NOTICE', 'WARNING', 'ERROR', 'CRITICAL']:
        LOGLEVEL = 'INFO'

LOGSTACKS = ['SYSLOG']
_LOGSTACKS = os.getenv('LOGSTACKS')
if _LOGSTACKS:
    LOGSTACKS = _LOGSTACKS.upper().split(',')
    if not any(logstack in LOGSTACKS for logstack in ['FILE', 'SYSLOG', 'CONSOLE']):
        LOGSTACKS = ['SYSLOG']

#-----------------------------------------------------------------------------------------------------
_HTTP_API_LISTEN_IP = os.getenv('HTTP_API_LISTEN_IP')
HTTP_API_LISTEN_IP = '0.0.0.0'
if _HTTP_API_LISTEN_IP:
    HTTP_API_LISTEN_IP = _HTTP_API_LISTEN_IP

_HTTP_API_LISTEN_PORT = os.getenv('HTTP_API_LISTEN_PORT')
HTTP_API_LISTEN_PORT = 8080
if _HTTP_API_LISTEN_PORT and _HTTP_API_LISTEN_PORT.isdigit():
    HTTP_API_LISTEN_PORT = int(_HTTP_API_LISTEN_PORT)
#-----------------------------------------------------------------------------------------------------
# CENTRALIZED
#-----------------------------------------------------------------------------------------------------
# standalone ~ all in one server
_LIBRE_STANDALONE_MODEL = os.getenv('LIBRE_STANDALONE_MODEL')
LIBRE_STANDALONE_MODEL = False
if _LIBRE_STANDALONE_MODEL and _LIBRE_STANDALONE_MODEL.upper() in ['TRUE', '1', 'YES']:
    LIBRE_STANDALONE_MODEL = True

# run inside container
_LIBRE_CONTAINERIZED = os.getenv('LIBRE_CONTAINERIZED')
LIBRE_CONTAINERIZED = False
if _LIBRE_CONTAINERIZED and _LIBRE_CONTAINERIZED.upper() in ['TRUE', '1', 'YES']:
    LIBRE_CONTAINERIZED = True

_LIBRE_BUILTIN_REDIS = os.getenv('LIBRE_BUILTIN_REDIS')
LIBRE_BUILTIN_REDIS = False
if _LIBRE_BUILTIN_REDIS and _LIBRE_BUILTIN_REDIS.upper() in ['TRUE', '1', 'YES']:
    LIBRE_BUILTIN_REDIS = True

_LIBRE_BUILTIN_FIREWALL = os.getenv('LIBRE_BUILTIN_FIREWALL')
LIBRE_BUILTIN_FIREWALL = True
if _LIBRE_BUILTIN_FIREWALL and _LIBRE_BUILTIN_FIREWALL.upper() in ['FALSE', '0', 'NO']:
    LIBRE_BUILTIN_FIREWALL = False

#-----------------------------------------------------------------------------------------------------
# REDIS ENDPOINT
#-----------------------------------------------------------------------------------------------------
REDIS_HOST = os.getenv('REDIS_HOST')
if not REDIS_HOST:
    REDIS_HOST = '127.0.0.1'

_REDIS_PORT = os.getenv('REDIS_PORT')
REDIS_PORT = 6379
if _REDIS_PORT and _REDIS_PORT.isdigit():
    REDIS_PORT = int(_REDIS_PORT)

_REDIS_DB = os.getenv('REDIS_DB')
REDIS_DB = 0
if _REDIS_DB and _REDIS_DB.isdigit():
    REDIS_DB = int(_REDIS_DB)

REDIS_PASSWORD = os.getenv('REDIS_PASSWORD')
SCAN_COUNT = 1000
REDIS_TIMEOUT = 5
#-----------------------------------------------------------------------------------------------------
# VOICE ATTRIBUTES
#-----------------------------------------------------------------------------------------------------
SWCODECS = ['PCMA', 'PCMU', 'OPUS', 'G729', 'AMR', 'AMR-WB', 'GSM']
_BUILTIN_ACLS_ = ['rfc1918.auto', 'nat.auto', 'localnet.auto', 'loopback.auto', 'none', 'wan.auto',
                  'wan_v6.auto', 'wan_v4.auto', 'any_v6.auto', 'any_v4.auto', 'rfc6598.auto']
#-----------------------------------------------------------------------------------------------------
# SERVER PROPERTIES
#-----------------------------------------------------------------------------------------------------
DFT_CLUSTER_ATTRS = {
    "name": "defaults",
    "rtp_start_port": 16384,
    "rtp_end_port": 32767,
    "max_calls_per_second": 60,
    "max_concurrent_calls": 4000
}

#-----------------------------------------------------------------------------------------------------
# configuration-changing event bus, apply for all cluster member
CHANGE_CFG_CHANNEL = 'CHANGE_CFG_CHANNEL'
# security (firewall) event bus, apply for all cluster member
SECURITY_CHANNEL = 'SECURITY_CHANNEL'
FIREWALL_NFTCMD_CHANNEL = 'FIREWALL_NFTCMD_CHANNEL'
# apply for particular node, with specify by event content
PERNODE_CHANNEL = 'PERNODE_CHANNEL'

# CALL RECOVERY CAPABILITY
_CRC_CAPABILITY = os.getenv('CRC_CAPABILITY')
CRC_CAPABILITY = False
if _CRC_CAPABILITY and _CRC_CAPABILITY.upper() in ['TRUE', '1', 'YES']:
    CRC_CAPABILITY = True
CRC_PGSQL_HOST = os.getenv('CRC_PGSQL_HOST')
CRC_PGSQL_PORT = os.getenv('CRC_PGSQL_PORT')
CRC_PGSQL_DATABASE = os.getenv('CRC_PGSQL_DATABASE')
CRC_PGSQL_USERNAME = os.getenv('CRC_PGSQL_USERNAME')
CRC_PGSQL_PASSWORD = os.getenv('CRC_PGSQL_PASSWORD')

#-----------------------------------------------------------------------------------------------------
# HTTPCDR DATA
#-----------------------------------------------------------------------------------------------------
HTTPCDR_ENDPOINTS = os.getenv('HTTPCDR_ENDPOINTS')
if HTTPCDR_ENDPOINTS:
    HTTPCDR_ENDPOINTS = HTTPCDR_ENDPOINTS.split(',')
#-----------------------------------------------------------------------------------------------------
# CDR FILE
#-----------------------------------------------------------------------------------------------------
DISKCDR_ENABLE = bool(os.getenv('DISKCDR_ENABLE'))

_CDRFNAME_INTERVAL = os.getenv('CDRFNAME_INTERVAL')
CDRFNAME_INTERVAL = None
if _CDRFNAME_INTERVAL and _CDRFNAME_INTERVAL.isdigit():
    CDRFNAME_INTERVAL = int(_CDRFNAME_INTERVAL)

CDRFNAME_FMT = os.getenv('CDRFNAME_FMT')
if not CDRFNAME_FMT:
    CDRFNAME_FMT = '%Y-%m-%d.cdr.nice'
