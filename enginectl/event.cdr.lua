dofile("{{rundir}}/enginectl/utilities.lua")
---------------------------------------------------------------------------

local function cdrreport()
    local uuid = event:getHeader("Unique-ID")
    local seshid = event:getHeader("variable_X-LIBRE-SESHID")
    local direction = event:getHeader("Call-Direction")
    local sipprofile = event:getHeader("variable_sofia_profile_name")
    local context = event:getHeader("Caller-Context")
    local intconname = event:getHeader("variable_X-LIBRE-INTCONNAME")
    local gateway_name = event:getHeader("variable_sip_gateway_name")
    local user_agent = event:getHeader("variable_sip_user_agent")
    local callid = event:getHeader("variable_sip_call_id")
    local caller_name = event:getHeader("Caller-Caller-ID-Name")
    local caller_number = event:getHeader("Caller-Caller-ID-Number")
    local destination_number = event:getHeader("Caller-Destination-Number")
    --
    local start_time = event:getHeader("variable_start_epoch")
    local answer_time = event:getHeader("variable_answer_epoch")
    local end_time = event:getHeader("variable_end_epoch")
    local duration = event:getHeader("variable_billsec")
    --
    local sip_network_ip = event:getHeader("variable_sip_network_ip")
    local sip_network_port = event:getHeader("variable_sip_network_port")
    local sip_local_network_addr  = event:getHeader("variable_sip_local_network_addr")
    local sip_via_protocol = event:getHeader("variable_sip_via_protocol")
    local sip_req_uri = event:getHeader("variable_sip_req_uri") -- variable_sip_destination_url sip:84987654321@libre.io:5060;transport=udp
    --
    local remote_media_ip = event:getHeader("variable_remote_media_ip") 
    local remote_media_port = event:getHeader("variable_remote_media_port")
    local local_media_ip = event:getHeader("variable_local_media_ip")
    local local_media_port = event:getHeader("variable_local_media_port")
    local advertised_media_ip = event:getHeader("variable_advertised_media_ip")
    local read_codec = event:getHeader("variable_read_codec") 
    local write_codec = event:getHeader("variable_write_codec") 
    --
    local hangup_disposition = event:getHeader('variable_sip_hangup_disposition')
    local hangup_cause = event:getHeader("variable_hangup_cause")
    local libre_hangup_cause = event:getHeader("variable_X-LIBRE-HANGUP-CAUSE")
    local sip_hangup_cause = event:getHeader("variable_proto_specific_hangup_cause")
    local bridge_sip_hangup_cause = event:getHeader("variable_last_bridge_proto_specific_hangup_cause")
    local libre_sip_hangup_cause = event:getHeader("variable_X-LIBRE-SIP-HANGUP-CAUSE")
    local sip_redirected_to = event:getHeader("variable_sip_redirected_to")
    local rtp_has_crypto = event:getHeader("variable_rtp_has_crypto")
    --
    cdr_details = {
        uuid=uuid, 
        seshid=seshid, 
        direction=direction,
        sipprofile=sipprofile,
        context=context,
        nodeid=NODEID,
        intconname=intconname,
        gateway_name=gateway_name,
        user_agent=user_agent,
        callid=callid,
        caller_name=caller_name,
        caller_number=caller_number,
        destination_number=destination_number,
        start_time=start_time,
        answer_time=answer_time,
        end_time=end_time,
        duration=duration,
        sip_network_ip=sip_network_ip,
        sip_network_port=sip_network_port,
        sip_local_network_addr=sip_local_network_addr,
        sip_via_protocol=sip_via_protocol,
        sip_req_uri=sip_req_uri,
        remote_media_ip=remote_media_ip,
        remote_media_port=remote_media_port,
        local_media_ip=local_media_ip,
        local_media_port=local_media_port,
        advertised_media_ip=advertised_media_ip,
        read_codec=read_codec,
        write_codec=write_codec,
        hangup_disposition=hangup_disposition,
        hangup_cause=hangup_cause,
        libre_hangup_cause=libre_hangup_cause,
        sip_hangup_cause=sip_hangup_cause,
        bridge_sip_hangup_cause=bridge_sip_hangup_cause,
        libre_sip_hangup_cause=libre_sip_hangup_cause,
        sip_redirected_to=sip_redirected_to,
        rtp_has_crypto=rtp_has_crypto
    }

    -- push raw cdr to redis, may use "event:serialize('json')" if needed
    cdrjson = json.encode(cdr_details)
    if rdbstate then
        rdbconn:pipeline(function(pipe)
            pipe:rpush('cdr:queue:new', uuid)
            pipe:setex('cdr:detail:'..uuid, CDRTTL, cdrjson)
        end)
    else 
        filename = os.date("%Y-%m-%d")..'.cdr.raw.json'
        writefile(LOGDIR..'/cdr/'..filename, cdrjson)
        logify('module', 'enginectl', 'space', 'event:cdr', 'action', 'cdrreporter', 'error', 'rdbtimeout', 'data', cdrjson, 'donext', 'writefile', 'filename', filename)
    end
end

---------------------******************************---------------------
---------------------*****|       MAIN       |*****---------------------
---------------------******************************---------------------
local result, error = pcall(cdrreport)
if not result then
    logger("module=enginectl, space=event:cdr, action=exception, error="..tostring(error))
end
---- close log ----
syslog.closelog()



--[[

RECV EVENT                                                                                                                                                                                                   
Event-Name: CHANNEL_HANGUP_COMPLETE                                                                                                                                                                          
Core-UUID: dfdcfeb2-5c24-4b48-a0ac-a778456d3339                                                                                                                                                              
FreeSWITCH-Hostname: libresbc1                                                                                                                                                                               
FreeSWITCH-Switchname: libresbc1                                                                                                                                                                             
FreeSWITCH-IPv4: 188.166.185.82                                                                                                                                                                              
FreeSWITCH-IPv6: ::1                                                                                                                                                                                         
Event-Date-Local: 2021-05-22 03:35:56                                                                                                                                                                        
Event-Date-GMT: Sat, 22 May 2021 03:35:56 GMT                                                                                                                                                                
Event-Date-Timestamp: 1621654556763676                                                                                                                                                                       
Event-Calling-File: switch_core_state_machine.c                                                                                                                                                              
Event-Calling-Function: switch_core_session_reporting_state                                                                                                                                                  
Event-Calling-Line-Number: 947                                                                                                                                                                               
Event-Sequence: 16128                                                                                                                                                                                        
Hangup-Cause: NORMAL_CLEARING                                                                                                                                                                                
Channel-State: CS_REPORTING                                                                                                                                                                                  
Channel-Call-State: HANGUP                                                                                                                                                                                   
Channel-State-Number: 11                                                                                                                                                                                     
Channel-Name: sofia/outside/33123456789@13.228.87.44                                                                                                                                                         
Unique-ID: 88b4673b-ad2c-4e8b-8fd6-4ad10aeb9ab0                                                                                                                                                              
Call-Direction: inbound                                                                                                                                                                                      
Presence-Call-Direction: inbound                                                                                                                                                                             
Channel-HIT-Dialplan: true                                                                                                                                                                                   
Channel-Call-UUID: 88b4673b-ad2c-4e8b-8fd6-4ad10aeb9ab0                                                                                                                                                      
Answer-State: hangup                                                                                                                                                                                         
Hangup-Cause: NORMAL_CLEARING                                                                                                                                                                                
Channel-Read-Codec-Name: opus                                                                                                                                                                                
Channel-Read-Codec-Rate: 48000
Channel-Read-Codec-Bit-Rate: 0
Channel-Write-Codec-Name: opus
Channel-Write-Codec-Rate: 48000
Channel-Write-Codec-Bit-Rate: 0
Caller-Direction: inbound
Caller-Logical-Direction: inbound
Caller-Username: 33123456789
Caller-Dialplan: XML
Caller-Caller-ID-Name: Donald Trump
Caller-Caller-ID-Number: 33123456789
Caller-Orig-Caller-ID-Name: Donald Trump
Caller-Orig-Caller-ID-Number: 33123456789
Caller-Callee-ID-Name: Outbound Call
Caller-Callee-ID-Number: 84987654321
Caller-Network-Addr: 13.228.87.44
Caller-ANI: 33123456789
Caller-Destination-Number: 33123456
Caller-Unique-ID: 88b4673b-ad2c-4e8b-8fd6-4ad10aeb9ab0
Caller-Source: mod_sofia
Caller-Context: interconnection
Caller-Channel-Name: sofia/outside/33123456789@13.228.87.44
Caller-Profile-Index: 1
Caller-Profile-Created-Time: 1621654552783696
Caller-Channel-Created-Time: 1621654552783696
Caller-Channel-Answered-Time: 1621654552843675
Caller-Channel-Progress-Time: 0
Caller-Channel-Progress-Media-Time: 1621654552843675
Caller-Channel-Hangup-Time: 1621654556763676
Caller-Channel-Transfer-Time: 0
Caller-Channel-Resurrect-Time: 0
Caller-Channel-Bridged-Time: 1621654553343696
Caller-Channel-Last-Hold: 0
Caller-Channel-Hold-Accum: 0
Caller-Screen-Bit: false
Caller-Privacy-Hide-Name: false
Caller-Privacy-Hide-Number: false
Other-Type: originatee
Other-Leg-Direction: outbound
Other-Leg-Logical-Direction: inbound
Other-Leg-Username: 33123456789
Other-Leg-Dialplan: XML
Other-Leg-Caller-ID-Name: 6533123456789
Other-Leg-Caller-ID-Number: 6533123456789
Other-Leg-Orig-Caller-ID-Name: Donald Trump
Other-Leg-Orig-Caller-ID-Number: 33123456789
Other-Leg-Callee-ID-Name: Outbound Call
Other-Leg-Callee-ID-Number: 84987654321
Other-Leg-Network-Addr: 13.228.87.44
Other-Leg-ANI: 33123456789
Other-Leg-Destination-Number: 84987654321
Other-Leg-Unique-ID: b1072f22-cdab-42c2-bea1-a3f3730098e5
Other-Leg-Source: mod_sofia
Other-Leg-Context: interconnection
Other-Leg-Channel-Name: sofia/outside/84987654321
Other-Leg-Profile-Created-Time: 1621654552804532
Other-Leg-Channel-Created-Time: 1621654552804532
Other-Leg-Channel-Answered-Time: 1621654552823679
Other-Leg-Channel-Progress-Time: 0
Other-Leg-Channel-Progress-Media-Time: 0
Other-Leg-Channel-Hangup-Time: 0
Other-Leg-Channel-Transfer-Time: 0
Other-Leg-Channel-Resurrect-Time: 0
Other-Leg-Channel-Bridged-Time: 0
Other-Leg-Channel-Last-Hold: 0
Other-Leg-Channel-Hold-Accum: 0
Other-Leg-Screen-Bit: false
Other-Leg-Privacy-Hide-Name: false
Other-Leg-Privacy-Hide-Number: false
variable_direction: inbound
variable_uuid: 88b4673b-ad2c-4e8b-8fd6-4ad10aeb9ab0
variable_session_id: 3
variable_sip_from_user: 33123456789
variable_sip_from_uri: 33123456789@13.228.87.44
variable_sip_from_host: 13.228.87.44
variable_channel_name: sofia/outside/33123456789@13.228.87.44
variable_sip_local_network_addr: 188.166.185.82
variable_sip_network_ip: 13.228.87.44
variable_sip_network_port: 5060
variable_sip_invite_stamp: 1621654552783696
variable_acl_token: AWSFPBX@outside.libresbc
variable_sip_received_ip: 13.228.87.44
variable_sip_received_port: 5060
variable_sip_via_protocol: udp
variable_sip_authorized: true
variable_sip_acl_authed_by: _REALM_ACL_outside
variable_sip_acl_token: AWSFPBX@outside.libresbc
variable_x-routing-plan: gotocore
variable_user_name: AWSFPBX
variable_domain_name: outside.libresbc
variable_sip_from_user_stripped: 33123456789
variable_sofia_profile_name: outside
variable_sofia_profile_url: sip:mod_sofia@188.166.185.82:5060
variable_recovery_profile_name: outside
variable_sip_Remote-Party-ID: "Donald Trump" <sip:33123456789@13.228.87.44>;party=calling;privacy=off;screen=no
variable_sip_cid_type: rpid
variable_sip_allow: INVITE, ACK, CANCEL, OPTIONS, BYE, REFER, SUBSCRIBE, NOTIFY, INFO, PUBLISH, MESSAGE
variable_sip_req_user: 33123456
variable_sip_req_port: 5060
variable_sip_req_uri: 33123456@188.166.185.82:5060
variable_sip_req_host: 188.166.185.82
variable_sip_to_user: 33123456
variable_sip_to_port: 5060
variable_sip_to_uri: 33123456@188.166.185.82:5060
variable_sip_to_host: 188.166.185.82
variable_sip_contact_user: 33123456789
variable_sip_contact_port: 5060
variable_sip_contact_uri: 33123456789@13.228.87.44:5060
variable_sip_contact_host: 13.228.87.44
variable_sip_via_host: 13.228.87.44
variable_sip_via_port: 5060
variable_sip_via_rport: 5060
variable_max_forwards: 70
variable_switch_r_sdp: v=0
o=root 1198252565 1198252565 IN IP4 13.228.87.44
s=Asterisk PBX 13.11.2
c=IN IP4 13.228.87.44
t=0 0
m=audio 14382 RTP/AVP 107 8 0 101
a=rtpmap:107 opus/48000/2
a=fmtp:107 useinbandfec=1
a=rtpmap:8 PCMA/8000
a=rtpmap:0 PCMU/8000
a=rtpmap:101 telephone-event/8000
a=fmtp:101 0-16
a=ptime:20
a=maxptime:60
variable_ep_codec_string: mod_opus.opus@48000h@20i@2c,CORE_PCM_MODULE.PCMA@8000h@20i@64000b,CORE_PCM_MODULE.PCMU@8000h@20i@64000b                                                                            
variable_call_uuid: 88b4673b-ad2c-4e8b-8fd6-4ad10aeb9ab0                                                                                                                                                     
variable_X-LIBRE-SESSIONID: 5a9100fa-38ca-4c37-b0d7-d02bf025c075                                                                                                                                             
variable_X-LIBRE-INTCONNAME: AWSFPBX                                                                                                                                                                         
variable_rtp_secure_media: optional:AES_CM_128_HMAC_SHA1_80:AES_CM_128_HMAC_SHA1_32                                                                                                                          
variable_codec_string: OPUS,PCMA,PCMU,G729                                                                                                                                                                   
variable_sip_copy_custom_headers: false                                                                                                                                                                      
variable_continue_on_fail: true                                                                                                                                                                              
variable_hangup_after_bridge: true                                                                                                                                                                           
variable_call_timeout: 0
variable_fax_enable_t38: true
variable_media_mix_inbound_outbound_codecs: true
variable_nolocal: sip_cid_type: none
variable_nolocal: absolute_codec_string: PCMA,PCMU
variable_nolocal: origination_caller_id_name: 6533123456789
variable_nolocal: origination_caller_id_number: 6533123456789
variable_nolocal: originate_timeout: 90
variable_nolocal: fax_enable_t38: true
variable_nolocal: hangup_after_bridge: true
variable_nolocal: origination_uuid: b1072f22-cdab-42c2-bea1-a3f3730098e5
variable_nolocal: sip_h_X-LIBRE-ORIGIN-HOP: AWSFPBX
variable_sip_ph_X-LIBRE-NEXT-HOP: FREEPBX
variable_sip_rh_X-LIBRE-NEXT-HOP: FREEPBX
variable_current_application_data: nolocal:X-LIBRE-INTCONNAME=FREEPBX
variable_current_application: export
variable_nolocal: X-LIBRE-INTCONNAME: FREEPBX
variable_export_vars: X-LIBRE-SESSIONID,sip_copy_custom_headers,media_mix_inbound_outbound_codecs,nolocal:sip_cid_type,nolocal:absolute_codec_string,nolocal:origination_caller_id_name,nolocal:origination_ca
ller_id_number,nolocal:originate_timeout,nolocal:fax_enable_t38,nolocal:hangup_after_bridge,nolocal:origination_uuid,nolocal:sip_h_X-LIBRE-ORIGIN-HOP,nolocal:X-LIBRE-INTCONNAME
variable_originated_legs: b1072f22-cdab-42c2-bea1-a3f3730098e5;Outbound Call;84987654321
variable_switch_m_sdp: v=0
o=root 2037510185 2037510185 IN IP4 13.228.87.44
s=Asterisk PBX 13.11.2
c=IN IP4 13.228.87.44
t=0 0
m=audio 11856 RTP/AVP 8 0 101
a=rtpmap:8 PCMA/8000
a=rtpmap:0 PCMU/8000
a=rtpmap:101 telephone-event/8000
a=fmtp:101 0-16
a=ptime:20
a=maxptime:150

variable_video_media_flow: inactive                                                                                                                                                                          
variable_text_media_flow: inactive                                                                                                                                                                           
variable_rtp_use_codec_string: OPUS,PCMA,PCMU,G729
variable_remote_video_media_flow: inactive
variable_remote_text_media_flow: inactive
variable_remote_audio_media_flow: sendrecv
variable_audio_media_flow: sendrecv
variable_rtp_audio_recv_pt: 107
variable_rtp_use_codec_name: opus
variable_rtp_use_codec_fmtp: useinbandfec=1
variable_rtp_use_codec_rate: 48000
variable_rtp_use_codec_ptime: 20
variable_rtp_use_codec_channels: 1
variable_rtp_last_audio_codec_string: opus@48000h@20i@1c
variable_read_codec: opus
variable_original_read_codec: opus
variable_read_rate: 48000
variable_original_read_rate: 48000
variable_write_codec: opus
variable_write_rate: 48000
variable_dtmf_type: rfc2833
variable_local_media_ip: 188.166.185.82
variable_local_media_port: 22978
variable_advertised_media_ip: 188.166.185.82
variable_rtp_use_timer_name: soft
variable_rtp_use_pt: 107
variable_rtp_use_ssrc: 4172278768
variable_rtp_2833_send_payload: 101
variable_rtp_2833_recv_payload: 101
variable_remote_media_ip: 13.228.87.44
variable_remote_media_port: 14382
variable_rtp_local_sdp_str: v=0
o=LibreSDP 1621631574 1621631575 IN IP4 188.166.185.82
s=LibreSDP
c=IN IP4 188.166.185.82
t=0 0
m=audio 22978 RTP/AVP 107 101
a=rtpmap:107 opus/48000/2
a=fmtp:107 useinbandfec=1; usedtx=1; maxaveragebitrate=64000; maxplaybackrate=48000; sprop-maxcapturerate=48000
a=rtpmap:101 telephone-event/8000
a=fmtp:101 0-16
a=silenceSupp:off - - - -
a=ptime:20
a=sendrecv

variable_endpoint_disposition: ANSWER                                                                                                                                                                        
variable_originate_disposition: SUCCESS                                                                                                                                                                      
variable_DIALSTATUS: SUCCESS                                                                                                                                                                                 
variable_originate_causes: b1072f22-cdab-42c2-bea1-a3f3730098e5;NONE                                                                                                                                         
variable_sip_to_tag: jSeKmX6ec908m                                                                                                                                                                           
variable_sip_from_tag: as5f8208c3                                                                                                                                                                            
variable_sip_cseq: 102                                                                                                                                                                                       
variable_sip_call_id: 3ce07fec6b701b334dddaf8f35c388c5@13.228.87.44:5060                                                                                                                                     
variable_sip_full_via: SIP/2.0/UDP 13.228.87.44:5060;branch=z9hG4bK59b3085d;rport=5060                                                                                                                       
variable_sip_from_display: Donald Trump                                                                                                                                                                      
variable_sip_full_from: "Donald Trump" <sip:33123456789@13.228.87.44>;tag=as5f8208c3                                                                                                                         
variable_sip_full_to: <sip:33123456@188.166.185.82:5060>;tag=jSeKmX6ec908m                                                                                                                                   
variable_last_bridge_to: b1072f22-cdab-42c2-bea1-a3f3730098e5                                                                                                                                                
variable_bridge_channel: sofia/outside/84987654321                                                                                                                                                           
variable_bridge_uuid: b1072f22-cdab-42c2-bea1-a3f3730098e5
variable_signal_bond: b1072f22-cdab-42c2-bea1-a3f3730098e5
variable_last_sent_callee_id_name: Outbound Call
variable_last_sent_callee_id_number: 84987654321
variable_sip_term_status: 200
variable_proto_specific_hangup_cause: sip:200
variable_sip_term_cause: 16
variable_sip_bye_h_X-Asterisk-HangupCause: Normal Clearing
variable_sip_bye_h_X-Asterisk-HangupCauseCode: 16
variable_last_bridge_role: originator
variable_sip_user_agent: QAPBX13
variable_sip_hangup_disposition: recv_bye
variable_bridge_hangup_cause: NORMAL_CLEARING
variable_hangup_cause: NORMAL_CLEARING
variable_hangup_cause_q850: 16
variable_digits_dialed: none
variable_start_stamp: 2021-05-22 03:35:52
variable_profile_start_stamp: 2021-05-22 03:35:52
variable_answer_stamp: 2021-05-22 03:35:52
variable_bridge_stamp: 2021-05-22 03:35:53
variable_progress_media_stamp: 2021-05-22 03:35:52
variable_end_stamp: 2021-05-22 03:35:56
variable_start_epoch: 1621654552
variable_start_uepoch: 1621654552783696
variable_profile_start_epoch: 1621654552
variable_profile_start_uepoch: 1621654552783696
variable_answer_epoch: 1621654552
variable_answer_uepoch: 1621654552843675
variable_bridge_epoch: 1621654553
variable_bridge_uepoch: 1621654553343696
variable_last_hold_epoch: 0
variable_last_hold_uepoch: 0
variable_hold_accum_seconds: 0
variable_hold_accum_usec: 0
variable_hold_accum_ms: 0
variable_resurrect_epoch: 0
variable_resurrect_uepoch: 0
variable_progress_epoch: 0
variable_progress_uepoch: 0
variable_progress_media_epoch: 1621654552
variable_progress_media_uepoch: 1621654552843675
variable_end_epoch: 1621654556
variable_end_uepoch: 1621654556763676
variable_last_app: export
variable_last_arg: nolocal:X-LIBRE-INTCONNAME=FREEPBX
variable_caller_id: "Donald Trump" <33123456789>
variable_duration: 4
variable_billsec: 4
variable_progresssec: 0
variable_answersec: 0
variable_waitsec: 1
variable_progress_mediasec: 0
variable_flow_billsec: 4
variable_mduration: 3980
variable_billmsec: 3920
variable_progressmsec: 0
variable_answermsec: 60
variable_waitmsec: 560
variable_progress_mediamsec: 60
variable_flow_billmsec: 3980
variable_uduration: 3979980
variable_billusec: 3920001
variable_progressusec: 0
variable_answerusec: 59979
variable_waitusec: 560000
variable_progress_mediausec: 59979
variable_flow_billusec: 3979980
variable_rtp_audio_in_raw_bytes: 12627
variable_rtp_audio_in_media_bytes: 12627
variable_rtp_audio_in_packet_count: 134
variable_rtp_audio_in_media_packet_count: 134
variable_rtp_audio_in_skip_packet_count: 62
variable_rtp_audio_in_jitter_packet_count: 0
variable_rtp_audio_in_dtmf_packet_count: 0
variable_rtp_audio_in_cng_packet_count: 0
variable_rtp_audio_in_flush_packet_count: 0
variable_rtp_audio_in_largest_jb_size: 0
variable_rtp_audio_in_jitter_min_variance: 6.42
variable_rtp_audio_in_jitter_max_variance: 201.51
variable_rtp_audio_in_jitter_loss_rate: 0.00
variable_rtp_audio_in_jitter_burst_rate: 0.00
variable_rtp_audio_in_mean_interval: 20.77
variable_rtp_audio_in_flaw_total: 12
variable_rtp_audio_in_quality_percentage: 76.00
variable_rtp_audio_in_mos: 3.86
variable_rtp_audio_out_raw_bytes: 22987
variable_rtp_audio_out_media_bytes: 22987
variable_rtp_audio_out_packet_count: 167
variable_rtp_audio_out_media_packet_count: 167
variable_rtp_audio_out_skip_packet_count: 0
variable_rtp_audio_out_dtmf_packet_count: 0
variable_rtp_audio_out_cng_packet_count: 0
variable_rtp_audio_rtcp_packet_count: 0
variable_rtp_audio_rtcp_octet_count: 0
]]



--[[ OUTBOUND

RECV EVENT                                                                                                                                                                                                   
Event-Name: CHANNEL_HANGUP_COMPLETE                                                                                                                                                                          
Core-UUID: dfdcfeb2-5c24-4b48-a0ac-a778456d3339                                                                                                                                                              
FreeSWITCH-Hostname: libresbc1                                                                                                                                                                               
FreeSWITCH-Switchname: libresbc1                                                                                                                                                                             
FreeSWITCH-IPv4: 188.166.185.82                                                                                                                                                                              
FreeSWITCH-IPv6: ::1                                                                                                                                                                                         
Event-Date-Local: 2021-05-22 03:35:56                                                                                                                                                                        
Event-Date-GMT: Sat, 22 May 2021 03:35:56 GMT                                                                                                                                                                
Event-Date-Timestamp: 1621654556763676                                                                                                                                                                       
Event-Calling-File: switch_core_state_machine.c                                                                                                                                                              
Event-Calling-Function: switch_core_session_reporting_state                                                                                                                                                  
Event-Calling-Line-Number: 947                                                                                                                                                                               
Event-Sequence: 16122                                                                                                                                                                                        
Hangup-Cause: NORMAL_CLEARING                                                                                                                                                                                
Channel-State: CS_REPORTING                                                                                                                                                                                  
Channel-Call-State: HANGUP                                                                                                                                                                                   
Channel-State-Number: 11                                                                                                                                                                                     
Channel-Name: sofia/outside/84987654321                                                                                                                                                                      
Unique-ID: b1072f22-cdab-42c2-bea1-a3f3730098e5                                                                                                                                                              
Call-Direction: outbound                                                                                                                                                                                     
Presence-Call-Direction: outbound                                                                                                                                                                            
Channel-HIT-Dialplan: false                                                                                                                                                                                  
Channel-Call-UUID: 88b4673b-ad2c-4e8b-8fd6-4ad10aeb9ab0                                                                                                                                                      
Answer-State: hangup                                                                                                                                                                                         
Hangup-Cause: NORMAL_CLEARING
Channel-Read-Codec-Name: PCMA
Channel-Read-Codec-Rate: 8000
Channel-Read-Codec-Bit-Rate: 64000
Channel-Write-Codec-Name: PCMA
Channel-Write-Codec-Rate: 8000
Channel-Write-Codec-Bit-Rate: 64000
Caller-Direction: outbound
Caller-Logical-Direction: outbound                                                                                                                                                                  [698/2075]
Caller-Username: 33123456789                                                                          
Caller-Dialplan: XML                                                                                  
Caller-Caller-ID-Name: 6533123456789
Caller-Caller-ID-Number: 6533123456789
Caller-Orig-Caller-ID-Name: Donald Trump
Caller-Orig-Caller-ID-Number: 33123456789
Caller-Callee-ID-Name: Outbound Call
Caller-Callee-ID-Number: 84987654321
Caller-Network-Addr: 13.228.87.44                                                                                                                                                                            
Caller-ANI: 33123456789                                                                               
Caller-Destination-Number: 84987654321                                                                
Caller-Unique-ID: b1072f22-cdab-42c2-bea1-a3f3730098e5
Caller-Source: mod_sofia                                                                              
Caller-Context: interconnection                                                                       
Caller-Channel-Name: sofia/outside/84987654321                                                        
Caller-Profile-Index: 1                                                                               
Caller-Profile-Created-Time: 1621654552804532
Caller-Channel-Created-Time: 1621654552804532
Caller-Channel-Answered-Time: 1621654552823679                                                        
Caller-Channel-Progress-Time: 0        
Caller-Channel-Progress-Media-Time: 0
Caller-Channel-Hangup-Time: 1621654556763676
Caller-Channel-Transfer-Time: 0                                                                                                                                                                              
Caller-Channel-Resurrect-Time: 0                                                                                                                                                                             
Caller-Channel-Bridged-Time: 1621654553343696
Caller-Channel-Last-Hold: 0       
Caller-Channel-Hold-Accum: 0                  
Caller-Screen-Bit: false     
Caller-Privacy-Hide-Name: false
Caller-Privacy-Hide-Number: false
Other-Type: originator
Other-Leg-Direction: inbound        
Other-Leg-Logical-Direction: inbound        
Other-Leg-Username: 33123456789      
Other-Leg-Dialplan: XML                       
Other-Leg-Caller-ID-Name: Donald Trump                                                                
Other-Leg-Caller-ID-Number: 33123456789
Other-Leg-Orig-Caller-ID-Name: Donald Trump
Other-Leg-Orig-Caller-ID-Number: 33123456789
Other-Leg-Network-Addr: 13.228.87.44
Other-Leg-ANI: 33123456789
Other-Leg-Destination-Number: 33123456
Other-Leg-Unique-ID: 88b4673b-ad2c-4e8b-8fd6-4ad10aeb9ab0
Other-Leg-Source: mod_sofia                   
Other-Leg-Context: interconnection
Other-Leg-Channel-Name: sofia/outside/33123456789@13.228.87.44
Other-Leg-Profile-Created-Time: 0
Other-Leg-Channel-Created-Time: 0                                                                     
Other-Leg-Channel-Answered-Time: 0
Other-Leg-Channel-Progress-Time: 0
Other-Leg-Channel-Progress-Media-Time: 0
Other-Leg-Channel-Hangup-Time: 0
Other-Leg-Channel-Transfer-Time: 0
Other-Leg-Channel-Resurrect-Time: 0
Other-Leg-Channel-Bridged-Time: 0
Other-Leg-Channel-Last-Hold: 0    
Other-Leg-Channel-Hold-Accum: 0
Other-Leg-Screen-Bit: false      
Other-Leg-Privacy-Hide-Name: false
Other-Leg-Screen-Bit: false                                                                                                                                                                         [640/2075]
Other-Leg-Privacy-Hide-Name: false                                                                    
Other-Leg-Privacy-Hide-Number: false                                                                  
variable_direction: outbound       
variable_is_outbound: true           
variable_uuid: b1072f22-cdab-42c2-bea1-a3f3730098e5
variable_session_id: 4                  
variable_sip_gateway_name: pbxtcp  
variable_sip_profile_name: gateway 
variable_text_media_flow: disabled                                                                                                                                                                           
variable_channel_name: sofia/outside/84987654321                                                      
variable_sip_destination_url: sip:84987654321@13.228.87.44:5060;transport=tcp                         
variable_max_forwards: 69                                                                             
variable_originator_codec: mod_opus.opus@48000h@20i@2c,CORE_PCM_MODULE.PCMA@8000h@20i@64000b,CORE_PCM_MODULE.PCMU@8000h@20i@64000b
variable_originator: 88b4673b-ad2c-4e8b-8fd6-4ad10aeb9ab0                                             
variable_switch_m_sdp: v=0                                                                            
o=root 1198252565 1198252565 IN IP4 13.228.87.44                                                      
s=Asterisk PBX 13.11.2                      
c=IN IP4 13.228.87.44                       
t=0 0                                                                                                 
m=audio 14382 RTP/AVP 107 8 0 101      
a=rtpmap:107 opus/48000/2           
a=fmtp:107 useinbandfec=1                  
a=rtpmap:8 PCMA/8000                                                                                                                                                                                         
a=rtpmap:0 PCMU/8000                                                                                                                                                                                         
a=rtpmap:101 telephone-event/8000           
a=fmtp:101 0-16                   
a=ptime:20                                    
a=maxptime:60                
                                                 
variable_export_vars: X-LIBRE-SESSIONID,sip_copy_custom_headers,media_mix_inbound_outbound_codecs,nolocal:sip_cid_type,nolocal:absolute_codec_string,nolocal:origination_caller_id_name,nolocal:origination_ca
ller_id_number,nolocal:originate_timeout,nolocal:fax_enable_t38,nolocal:hangup_after_bridge,nolocal:origination_uuid,nolocal:sip_h_X-LIBRE-ORIGIN-HOP,nolocal:X-LIBRE-INTCONNAME
variable_X-LIBRE-SESSIONID: 5a9100fa-38ca-4c37-b0d7-d02bf025c075
variable_sip_copy_custom_headers: false     
variable_media_mix_inbound_outbound_codecs: true
variable_sip_cid_type: none                   
variable_absolute_codec_string: PCMA,PCMU                                                             
variable_origination_caller_id_name: 6533123456789
variable_origination_caller_id_number: 6533123456789
variable_originate_timeout: 90             
variable_fax_enable_t38: true      
variable_hangup_after_bridge: true
variable_origination_uuid: b1072f22-cdab-42c2-bea1-a3f3730098e5
variable_sip_h_X-LIBRE-ORIGIN-HOP: AWSFPBX                                                            
variable_X-LIBRE-INTCONNAME: FREEPBX          
variable_originate_early_media: true
variable_originating_leg_uuid: 88b4673b-ad2c-4e8b-8fd6-4ad10aeb9ab0
variable_audio_media_flow: sendrecv
variable_video_media_flow: sendrecv                                                                   
variable_rtp_local_sdp_str: v=0  
o=LibreSDP 1621643820 1621643821 IN IP4 188.166.185.82
s=LibreSDP                             
c=IN IP4 188.166.185.82        
t=0 0                            
m=audio 10732 RTP/AVP 8 0 101     
a=rtpmap:8 PCMA/8000            
a=rtpmap:0 PCMU/8000              
a=rtpmap:101 telephone-event/8000
a=fmtp:101 0-16                  
a=silenceSupp:off - - - -       
a=fmtp:101 0-16                                                                                                                                                                                     [582/2075]
a=silenceSupp:off - - - -                                                                             
a=ptime:20                                                                                            
a=sendrecv                         
                                                 
variable_sip_outgoing_contact_uri: <sip:gw+pbxtcp@188.166.185.82:5060;transport=tcp;gw=pbxtcp>
variable_sip_req_uri: 84987654321@13.228.87.44:5060;transport=tcp
variable_sofia_profile_name: outside
variable_recovery_profile_name: outside
variable_sofia_profile_url: sip:mod_sofia@188.166.185.82:5060                                                                                                                                                
variable_sip_local_network_addr: 188.166.185.82                                                       
variable_sip_reply_host: 13.228.87.44                                                                 
variable_sip_reply_port: 5060                                                                         
variable_sip_network_ip: 13.228.87.44                                                                                                                                                                        
variable_sip_network_port: 5060                                                                       
variable_sip_user_agent: QAPBX13                                                                      
variable_sip_allow: INVITE, ACK, CANCEL, OPTIONS, BYE, REFER, SUBSCRIBE, NOTIFY, INFO, PUBLISH, MESSAGE
variable_sip_recover_contact: <sip:84987654321@13.228.87.44:5060;transport=TCP>
variable_sip_full_via: SIP/2.0/TCP 188.166.185.82;branch=z9hG4bK1tNeF9y2vZ9ZD;received=188.166.185.82;rport=40241
variable_sip_recover_via: SIP/2.0/TCP 188.166.185.82;branch=z9hG4bK1tNeF9y2vZ9ZD;received=188.166.185.82;rport=40241
variable_sip_from_display: 6533123456789
variable_sip_full_from: "6533123456789" <sip:6533123456789@188.166.185.82>;tag=K27BprQj9HQUg
variable_sip_full_to: <sip:84987654321@13.228.87.44:5060;transport=tcp>;tag=as666c2507
variable_sip_from_user: 6533123456789                                                                                                                                                                        
variable_sip_from_uri: 6533123456789@188.166.185.82                                                                                                                                                          
variable_sip_from_host: 188.166.185.82      
variable_sip_to_params: transport=tcp
variable_sip_to_user: 84987654321             
variable_sip_to_port: 5060   
variable_sip_to_uri: 84987654321@13.228.87.44:5060
variable_sip_to_host: 13.228.87.44                                                                                                                                                                           
variable_sip_contact_params: transport=TCP                                                                                                                                                                   
variable_sip_contact_user: 84987654321                                                                
variable_sip_contact_port: 5060             
variable_sip_contact_uri: 84987654321@13.228.87.44:5060
variable_sip_contact_host: 13.228.87.44       
variable_sip_to_tag: as666c2507                                                                       
variable_sip_from_tag: K27BprQj9HQUg             
variable_sip_cseq: 36273484                                                                           
variable_sip_call_id: a69096bb-3551-123a-2e8c-ea0e9328da5f
variable_switch_r_sdp: v=0         
o=root 2037510185 2037510185 IN IP4 13.228.87.44
s=Asterisk PBX 13.11.2                                                                                
c=IN IP4 13.228.87.44                                                                                 
t=0 0                                         
m=audio 11856 RTP/AVP 8 0 101      
a=rtpmap:8 PCMA/8000                                                                                  
a=rtpmap:0 PCMU/8000              
a=rtpmap:101 telephone-event/8000                                                                     
a=fmtp:101 0-16                  
a=ptime:20                                                                                            
a=maxptime:150                         
                                                 
variable_ep_codec_string: CORE_PCM_MODULE.PCMA@8000h@20i@64000b,CORE_PCM_MODULE.PCMU@8000h@20i@64000b
variable_rtp_use_codec_string: PCMA,PCMU
variable_remote_video_media_flow: inactive
variable_remote_text_media_flow: inactive
variable_remote_audio_media_flow: sendrecv
variable_rtp_audio_recv_pt: 8    
variable_rtp_use_codec_name: PCMA
variable_rtp_use_codec_name: PCMA                                                                                                                                                                   [523/2075]
variable_rtp_use_codec_rate: 8000                                                                                                                                                                            
variable_rtp_use_codec_ptime: 20                                                                                                                                                                             
variable_rtp_use_codec_channels: 1                                                                                                                                                                           
variable_rtp_last_audio_codec_string: PCMA@8000h@20i@1c
variable_read_codec: PCMA
variable_original_read_codec: PCMA
variable_read_rate: 8000
variable_original_read_rate: 8000
variable_write_codec: PCMA
variable_write_rate: 8000
variable_dtmf_type: rfc2833
variable_local_media_ip: 188.166.185.82
variable_local_media_port: 10732
variable_advertised_media_ip: 188.166.185.82
variable_rtp_use_timer_name: soft
variable_rtp_use_pt: 8
variable_rtp_use_ssrc: 4172998992
variable_rtp_2833_send_payload: 101
variable_rtp_2833_recv_payload: 101
variable_remote_media_ip: 13.228.87.44
variable_remote_media_port: 11856
variable_endpoint_disposition: ANSWER
variable_call_uuid: 88b4673b-ad2c-4e8b-8fd6-4ad10aeb9ab0
variable_last_bridge_to: 88b4673b-ad2c-4e8b-8fd6-4ad10aeb9ab0
variable_bridge_channel: sofia/outside/33123456789@13.228.87.44
variable_bridge_uuid: 88b4673b-ad2c-4e8b-8fd6-4ad10aeb9ab0
variable_signal_bond: 88b4673b-ad2c-4e8b-8fd6-4ad10aeb9ab0
variable_last_sent_callee_id_name: 6533123456789
variable_last_sent_callee_id_number: 6533123456789
variable_sip_hangup_phrase: OK
variable_last_bridge_hangup_cause: NORMAL_CLEARING
variable_last_bridge_proto_specific_hangup_cause: sip:200
variable_hangup_cause: NORMAL_CLEARING
variable_hangup_cause_q850: 16
variable_digits_dialed: none
variable_start_stamp: 2021-05-22 03:35:52
variable_profile_start_stamp: 2021-05-22 03:35:52
variable_answer_stamp: 2021-05-22 03:35:52
variable_bridge_stamp: 2021-05-22 03:35:53
variable_end_stamp: 2021-05-22 03:35:56
variable_start_epoch: 1621654552
variable_start_uepoch: 1621654552804532
variable_profile_start_epoch: 1621654552
variable_profile_start_uepoch: 1621654552804532
variable_answer_epoch: 1621654552
variable_answer_uepoch: 1621654552823679
variable_bridge_epoch: 1621654553
variable_bridge_uepoch: 1621654553343696
variable_last_hold_epoch: 0
variable_last_hold_uepoch: 0
variable_hold_accum_seconds: 0
variable_hold_accum_usec: 0
variable_hold_accum_ms: 0
variable_resurrect_epoch: 0
variable_resurrect_uepoch: 0
variable_progress_epoch: 0
variable_progress_uepoch: 0
variable_progress_media_epoch: 0
variable_progress_media_uepoch: 0
variable_progress_media_epoch: 0                                                                                                                                                                    [465/2075]
variable_progress_media_uepoch: 0                                                                                                                                                                            
variable_end_epoch: 1621654556                                                                                                                                                                               
variable_end_uepoch: 1621654556763676                                                                                                                                                                        
variable_caller_id: "6533123456789" <6533123456789>   
variable_duration: 4    
variable_billsec: 4              
variable_progresssec: 0
variable_answersec: 0           
variable_waitsec: 1      
variable_progress_mediasec: 0
variable_flow_billsec: 4  
variable_mduration: 3959              
variable_billmsec: 3940        
variable_progressmsec: 0                   
variable_answermsec: 19         
variable_waitmsec: 539
variable_progress_mediamsec: 0  
variable_flow_billmsec: 3959      
variable_uduration: 3959144       
variable_billusec: 3939997           
variable_progressusec: 0        
variable_answerusec: 19147          
variable_waitusec: 539164                                                                             
variable_progress_mediausec: 0                                                                        
variable_flow_billusec: 3959144                                                                       
variable_sip_hangup_disposition: send_bye                                                             
variable_rtp_audio_in_raw_bytes: 29412                                                                
variable_rtp_audio_in_media_bytes: 29240       
variable_rtp_audio_in_packet_count: 171          
variable_rtp_audio_in_media_packet_count: 170
variable_rtp_audio_in_skip_packet_count: 5       
variable_rtp_audio_in_jitter_packet_count: 0                                                          
variable_rtp_audio_in_dtmf_packet_count: 0
variable_rtp_audio_in_cng_packet_count: 0
variable_rtp_audio_in_flush_packet_count: 1
variable_rtp_audio_in_largest_jb_size: 0
variable_rtp_audio_in_jitter_min_variance: 6.15 
variable_rtp_audio_in_jitter_max_variance: 132.71
variable_rtp_audio_in_jitter_loss_rate: 0.00
variable_rtp_audio_in_jitter_burst_rate: 0.00
variable_rtp_audio_in_mean_interval: 20.00
variable_rtp_audio_in_flaw_total: 0   
variable_rtp_audio_in_quality_percentage: 100.00
variable_rtp_audio_in_mos: 4.50               
variable_rtp_audio_out_raw_bytes: 23048
variable_rtp_audio_out_media_bytes: 23048
variable_rtp_audio_out_packet_count: 134
variable_rtp_audio_out_media_packet_count: 134
variable_rtp_audio_out_skip_packet_count: 0
variable_rtp_audio_out_dtmf_packet_count: 0
variable_rtp_audio_out_cng_packet_count: 0
variable_rtp_audio_rtcp_packet_count: 0
variable_rtp_audio_rtcp_octet_count: 0
]]
