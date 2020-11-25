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

# SERVER PROPERTIES
NODENAME = '{{nodename}}'
CLUSTERNAME = '{{clustername}}'
CLUSTER_MEMBERS = {{cluster_members}}
