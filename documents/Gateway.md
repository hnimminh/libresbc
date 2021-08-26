<img src="https://img.shields.io/badge/STATUS-DONE-blue?style=flat-square">

## Introduce
**Gateway** is a logical unit for outbound interconnection, that needed to defined in advance. The gateway control the signaling, and policy  and maintain the connection between LibreSBC and other sip entities.

## Setting
<img src="https://img.shields.io/badge/API-/libreapi/base/gateway-BLUE?style=for-the-badge&logo=Safari">

Consider any setting that you want to add, following is the configuration parameters:

Parameter    | Category           | Description                     
:---         |:---                |:---                             
name         |`string` `required` | The name of gateway (unique)    
desc         |`string` | Description 
username |`string`| auth username
realm|`string`|auth realm, use gateway name as default
from_user|`string`|username in from header, use username as default
from_domain|`string`|domain in from header, use realm as default
password |`string`| auth password
extension|`string`|extension for inbound calls, use username as default
proxy|`string` `required`|farend proxy `ip address` or `domain`, use realm as default
port|`int` |farend destination port
transport|`enum`|farend transport protocol, `udp` `tcp` `tls`
do_register|`bool`|register to farend endpoint, false mean no register
register_proxy|`string`|proxy address to register, use proxy as default
register_transport|`enum`|transport to use for register, `udp` `tcp` `tls`
expire_seconds|`int`|register expire interval in second, use 600s as default
retry_seconds|`int`|interval in second before a retry when a failure or timeout occurs
caller_id_in_from|`bool`|use the callerid of an inbound call in the from field on outbound calls via this gateway
cid_type|`enum`|callerid header mechanism: `rpid`, `pid`, `none`
contact_params|`string`|extra sip params to send in the contact
extension_in_contact|`bool`|put the extension in the contact
ping|`int`|the period (second) to send SIP OPTION
ping_max|`int`|number of success pings to declaring a gateway up
ping_min|`int`|number of failure pings to declaring a gateway down

**Note**: In most of case you don't need to use all of these above params. Try to keep the thing simple.


