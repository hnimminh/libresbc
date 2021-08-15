json = require('json')

LAYER = '{{kamcfgs.name}}'
B2BUA_LOOPBACK_IPADDRS = {{swipaddrs}}
DOMAIN_POLICIES = json.decode('{{jsonpolicies}}')

AUTHFLOODING_THRESHOLD = {{kamcfgs.antiflooding.threshold}}
AUTHFLOODING_BANTIME = {{kamcfgs.antiflooding.bantime}}
AUTHFAILURE_THRESHOLD = {{kamcfgs.authfailure.threshold}}
AUTHFAILURE_BANTIME = {{kamcfgs.authfailure.bantime}}
ATTACKAVOID_THRESHOLD = {{kamcfgs.attackavoid.threshold}}
ATTACKAVOID_BANTIME = {{kamcfgs.attackavoid.bantime}}
