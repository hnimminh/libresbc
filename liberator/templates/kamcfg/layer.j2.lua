json = require('json')

LAYER = '{{layer}}'
SELFSW_IPADDRS = {{swipaddrs}}
DOMAIN_POLICIES = json.decode('{{jsonpolicies}}')
DFTDOMAIN = '{{dftdomain}}'

{%- if kamcfgs.antiflooding %}
AUTIFLOODING_THRESHOLD = {{kamcfgs.antiflooding.threshold}}
AUTIFLOODING_BANTIME = {{kamcfgs.antiflooding.bantime}}
{%- endif %}
AUTHFAILURE_THRESHOLD = {{kamcfgs.authfailure.threshold}}
AUTHFAILURE_BANTIME = {{kamcfgs.authfailure.bantime}}
ATTACKAVOID_THRESHOLD = {{kamcfgs.attackavoid.threshold}}
ATTACKAVOID_BANTIME = {{kamcfgs.attackavoid.bantime}}

BRANCH_NATOUT_FLAG = {{_KAMCONST.BRANCH_NATOUT_FLAG}}
BRANCH_NATSIPPING_FLAG = {{_KAMCONST.BRANCH_NATSIPPING_FLAG}}
LIBRE_USER_LOCATION = '{{_KAMCONST.LIBRE_USER_LOCATION}}'
