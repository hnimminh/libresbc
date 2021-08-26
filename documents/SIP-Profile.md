<img src="https://img.shields.io/badge/STATUS-DONE-blue?style=flat-square">

## Introduce
**SIP Profile/Interface** is an application layer interface logically residing over a network interface. The SIP profile defines the transport addresses (IP address and port) upon which the LibreSBC receives and sends SIP messages and RTP packets as well as related rtp media and signalling setting. You can define a SIP profile for each network to which the LibreSBC is connected. SIP profile support UDP, TCP and TLS transport. In addition to defining a SIP Profile's IP address might be defined by NetAlias API.

## Setting
<img src="https://img.shields.io/badge/API-/libreapi/sipprofile-BLUE?style=for-the-badge&logo=Safari">

Consider any setting that you want to add, following is the configuration parameters:

Parameter    | Category           | Description                     
:---         |:---                |:---                             
name         |`string` `required` | The name of profile (unique)    
desc         |`string` | Description                     
user_agent   |`string` | The value will be displayed as User-Agent in SIP header. Default is `LibreSBC`
sdp_user     |`string` | The username of the o= and s= fields in SDP body
local_network_acl |`string`|Set the local network that refer from predefined acl 
enable_100rel |`bool` | Reliability - PRACK message as defined in RFC3262
ignore_183nosdp|`bool`| Just ignore SIP 183 without SDP body
sip_options_respond_503_on_busy |`bool`|response 503 when system is in heavy load
disable_transfer|`bool`|true mean disable call transfer
manual_redirect|`bool`|how call forward handled, true mean it be controlled under libresbc contraints, false mean it be work automatically
enable_3pcc|`bool`|determines if third party call control is allowed or not
enable_compact_headers|`bool`|disable as default, true to enable compact SIP headers
enable_timer|`bool`|true to support for RFC 4028 SIP Session Timers
session_timeout|`int`|call to expire after the specified seconds
minimum_session_expires|`int`|Value of SIP header Min-SE
dtmf_type|`enum`| Dual-tone multi-frequency (DTMF) signal type <br>`rfc2833` `info` `none`
media_timeout|`int`|The number of seconds of RTP inactivity before SBC considers the call disconnected, and hangs up (recommend to use session timers instead), default value is 0 - disables the timeout.
rtp_rewrite_timestamps|`bool`|set true to regenerate and rewrite the timestamps in all the RTP streams going to an endpoint using this SIP Profile, necessary to fix audio issues when sending calls to some paranoid and not RFC-compliant gateways
context      |`string` `required` | The dialplan context of SIP profile
sip_port| `int`|Port to bind to for SIP traffic
sip_address|`string` `required`|IP address via NetAlias use for SIP Signalling
rtp_address|`string` `required`|IP address via NetAlias use for RTP Media
tls          |`bool` | Enable TLS transport
tls_only|`bool`|set True to disable listening on the unencrypted port for this connection
sips_port|`int`|Port to bind to for TLS SIP traffic

