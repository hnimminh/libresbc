json = require('json')

NODEID = '{{nodeid}}'
LAYER = '{{layer}}'
B2BUA_LOOPBACK_IPADDRS = {{swipaddrs}}
DOMAIN_POLICIES = json.decode('{{jsonpolicies}}')

AUTHFAILURE_THREDHOLD = 20
AUTHFAILURE_WINDOW = 600
BRUTEFORCE_THREDHOLD = 5
BRUTEFORCE_WINDOW = 18000
