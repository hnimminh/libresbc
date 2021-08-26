<img src="https://img.shields.io/badge/STATUS-DONE-blue?style=flat-square">

## Introduce
* What is interconnection: [[Interconnection]]

**Outbound Interconnection** indicate the policies in caller, media, interoperability, rate limiting, load balancing algorithm, etc for outbound direction

## Setting
<img src="https://img.shields.io/badge/API-/libreapi/interconnection/outbound-BLUE?style=for-the-badge&logo=Safari">

Consider any setting that you want to add, following is the configuration parameters:

Parameter    | Category           | Description                     
:---         |:---                |:---                             
name         |`string` `required` | The name of gateway (unique)    
desc         |`string` | Description 
sipprofile |`string` `required`|a sip profile nameid that interconnection engage to
distribution|`enum` `required`| The dispatcher algorithm to selects a destination from addresses set.<br>`weight_based` `round_robin` `hash_callid` `hash_src_ip` `hash_destination_number`
gateways|`list` `required`|gateway list used for this interconnection
rtpaddrs|`string` |a set of IPv4 Network that use for RTP
media_class|`string` `required`|nameid of media class
capacity_class|`list` `required`|list nameid of capacity class
translation_classes|`list` `required`|list nameid of translation class
manipulation_classes|`list` `required`|list nameid of manipulation class
privacy|`list` `required`| privacy header, `auto` `none` `screen` `name` `number`
cid_type|`enum`|callerid header mechanism: `rpid`, `pid`, `none`
nodes|`list`|a set of node member that interconnection engage to
enable|`bool`|enable/disable this interconnection

**Gateway Map**

Parameter    | Category           | Description                     
:---         |:---                |:---                             
name         |`string` `required` | gateway name    
weight       |`int` `required`| weight value use for distribution 
