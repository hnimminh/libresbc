<img src="https://img.shields.io/badge/STATUS-DONE-blue?style=flat-square"><br/><br/>
When you make a phone call to another phone number, from the perspective of the LibreSBC, there are 2 parts/legs of the call session:
* Ingress (aka A leg or the incoming call leg) **to** the LibreSBC is the incoming connection from the originator (caller)
* Egress (aka B leg the outgoing call leg) **from** the LibreSBC is the outbound connection to the recipient of the call (callee)

Call Detail Records are the data recorded during each call session, each leg will have it own CDR.


Parameter                | Description                     
:------------------------|:----------------------------------------------------                   
uuid                     |CDR uuid, unique per leg
seshid                   |Session id, unique per call session
direction                |Call direction, `inbound` `outbound`
sipprofile               |SIP profile name where call was engaged
context                  |Context of sip profile
nodeid                   |SBC node id where call was processed
intconname               |Interconnection name
gateway                  |Gateway name, available for outbound direction only
user_agent               |SIP user agent, derived from SIP user agent header
callid                   |SIP Call ID, derived from SIP call id header
caller_name              |Caller name
caller_number            |Caller number
destination_number       |Destination number
start_time               |epochtime when call was started
answer_time              |epochtime when call was answered
progress_time            |epochtime when 180 Ringing was process
progress_media_time      |epochtime when first media was process (it can be 183 early media or 200 OK)
end_time                 |epochtime when call was hanged up
duration                 |call duration in second, end_time - answer_time
sip_network_ip           |IP address of interconnection via SIP protocol
sip_network_port         |Port number of interconnection via SIP protocol
sip_local_network_add    |IP address of SBC via SIP connection
transport                |Transport protocol `udp` `tcp` `tls`
remote_media_ip          |IP address of interconnection via RTP protocol
remote_media_port        |Port number of interconnection via RTP protocol
local_media_ip           |IP address of SBC via RTP connection
local_media_port         |Port number of SBC via RTP protocol
read_codec               |Media codec used by interconnection
write_codec              |Media codec used by SBC
rtp_crypto               |Media encryption algo used for SRTP
hangup_cause             |Cause why call was released
sip_resp_code            |SIP final response code, eg: sip:487
disposition              |Who hangup the call
status                   |alias of `sip_resp_code`


How to measure call metric?

* billable duration = `end_time` - `answer_time` (duration)
* waiting time for answering = `answer_time` - `start_time`
* waiting time for ringing = `progress_time` - `start_time` or `progress_media_time` - `start_time` (if progress_time=0)
* if call answered: ringing_duration = `answer_time` - `progress_time` or `answer_time` - `progress_media_time` (if progress_time=0)
* if call unanswered: ringing_duration = `end_time` - `progress_time` or `end_time` - `progress_media_time` (if progress_time=0)