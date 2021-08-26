<img src="https://img.shields.io/badge/STATUS-DONE-blue?style=flat-square">

## Introduce
* What is interconnection: [[Interconnection]]

**Inbound Interconnection** indicate the policies in caller, media, interoperability, rate limiting, and more on Announcement, ringtone with PreAnswer, Authentication mechanism, etc for an inbound direction

## Setting
<img src="https://img.shields.io/badge/API-/libreapi/interconnection/inbound-BLUE?style=for-the-badge&logo=Safari">

Consider any setting that you want to add, following is the configuration parameters:

Parameter    | Category           | Description                     
:---         |:---                |:---                             
name         |`string` `required` | The name of gateway (unique)    
desc         |`string` | Description 
sipprofile |`string` `required`|a sip profile nameid that interconnection engage to
routing|`string`|routing table that will be used by this inbound interconnection
sipaddrs|`string`|set of sip signaling addresses that use for SIP
rtpaddrs|`string` |a set of IPv4 Network that use for RTP
ringready|`bool`|response 180 ring indication
media_class|`string` `required`|nameid of media class
capacity_class|`list` `required`|list nameid of capacity class
translation_classes|`list` `required`|list nameid of translation class
manipulation_classes|`list` `required`|list nameid of manipulation class
preanswer_class|`string` `required`| nameid of preanswer class
authscheme|`enum`|auth scheme for inbound, include: `ip`, `digest`, `both`
nodes|`list`|a set of node member that interconnection engage to
enable|`bool`|enable/disable this interconnection


