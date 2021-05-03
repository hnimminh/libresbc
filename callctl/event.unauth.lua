dofile("{{rundir}}/callctl/utilities.lua")
---------------------------------------------------------------------------

local function unauth()
    local profilename = event:getHeader("profile-name")
    local user_agent = event:getHeader("user-agent")
    local network_ip = event:getHeader("network-ip")
    logify('module', 'callflow', 'space', 'event:unauth', 'action', 'queue-block', 'profilename', profilename, 'user_agent', user_agent, 'network_ip', network_ip)
end
---------------------******************************---------------------
---------------------*****|       MAIN       |*****---------------------
---------------------******************************---------------------
local result, error = pcall(unauth)
if not result then
    logger("module=callctl, space=event:unauth, action=exception, error="..tostring(error))
end
---- close log ----
syslog.closelog()

--[[                                                                                                                                                                                                 
Event-Subclass: sofia::pre_register                                                                                                                                                                           
Event-Name: CUSTOM                                                                                                                                                                                            
Core-UUID: 3f277dce-1172-4628-aa59-ec977cdf319b                                                                                                                                                               
FreeSWITCH-Hostname: libresbc1                                                                                                                                                                                
FreeSWITCH-Switchname: libresbc1                                                                                                                                                                              
FreeSWITCH-IPv4: <LIBRESBC-IP>                                                                                                                                                                               
FreeSWITCH-IPv6: ::1                                                                                                                                                                                          
Event-Date-Local: 2021-05-03 05:20:40                                                                                                                                                                         
Event-Date-GMT: Mon, 03 May 2021 05:20:40 GMT                                                                                                                                                                 
Event-Date-Timestamp: 1620019240519134                                                                                                                                                                        
Event-Calling-File: sofia_reg.c                                                                                                                                                                               
Event-Calling-Function: sofia_reg_handle_register_token                                                                                                                                                       
Event-Calling-Line-Number: 1763                                                                                                                                                                               
Event-Sequence: 727                                                                                                                                                                                           
profile-name: outside                                                                                                                                                                                         
from-user: 33123456                                                                                                                                                                                           
from-host: <LIBRESBC-IP>                                                                                                                                                                                     
contact: "" <sip:3312345678@<FAREND-IP>:5060>                                                                                                                                                                
call-id: 52d9fa751db23cb752fbe220226a41b6@<FAREND-IP>:5060                                                                                                                                                   
rpid: unknown                                                                                                                                                                                                 
status: Registered(UDP)                                                                                                                                                                                       
expires: 300                                                                                                                                                                                                  
to-user: 3312345678                                                                                                                                                                                           
to-host: <FAREND-IP>                                                                                                                                                                                         
network-ip: <FAREND-IP>                                                                                                                                                                                      
network-port: 5060                                                                                                                                                                                            
user-agent: <FAREND-UA> 
                                                                                                                                                                                                
Event-Subclass: sofia::register_attempt                                                                                                                                                                       
Event-Name: CUSTOM                                                                                                                                                                                            
Core-UUID: 3f277dce-1172-4628-aa59-ec977cdf319b                                                                                                                                                               
FreeSWITCH-Hostname: libresbc1                                                                                                                                                                                
FreeSWITCH-Switchname: libresbc1                                                                                                                                                                              
FreeSWITCH-IPv4: <LIBRESBC-IP>                                                                                                                                                                               
FreeSWITCH-IPv6: ::1                                                                                                                                                                                          
Event-Date-Local: 2021-05-03 05:20:40                                                                                                                                                                         
Event-Date-GMT: Mon, 03 May 2021 05:20:40 GMT                                                                                                                                                                 
Event-Date-Timestamp: 1620019240539062                                                                                                                                                                        
Event-Calling-File: sofia_reg.c                                                                                                                                                                               
Event-Calling-Function: sofia_reg_handle_register_token                                                                                                                                                       
Event-Calling-Line-Number: 1558                                                                                                                                                                               
Event-Sequence: 730                                                                                                                                                                                           
profile-name: outside                                                                                                                                                                                         
from-user: 33123456                                                                                                                                                                                           
from-host: <LIBRESBC-IP>                                                                                                                                                                                     
contact: "" <sip:3312345678@<FAREND-IP>:5060>                                                                                                                                                                
call-id: 52d9fa751db23cb752fbe220226a41b6@<FAREND-IP>:5060                                                                                                                                                   
rpid: unknown                                                                                                                                                                                                 
status: Registered(UDP)                                                                                                                                                                                       
expires: 300                                                                                                                                                                                                  
to-user: 3312345678                                                                                                                                                                                           
to-host: <FAREND-IP>                                                                                                                                                                                         
network-ip: <FAREND-IP>
network-port: 5060
username: AWSFPBX
realm: outside.libresbc
user-agent: <FAREND-UA>
auth-result: FORBIDDEN

Event-Subclass: sofia::register_failure
Event-Name: CUSTOM
Core-UUID: 3f277dce-1172-4628-aa59-ec977cdf319b
FreeSWITCH-Hostname: libresbc1
FreeSWITCH-Switchname: libresbc1
FreeSWITCH-IPv4: <LIBRESBC-IP>
FreeSWITCH-IPv6: ::1
Event-Date-Local: 2021-05-03 05:20:40
Event-Date-GMT: Mon, 03 May 2021 05:20:40 GMT
Event-Date-Timestamp: 1620019240539062
Event-Calling-File: sofia_reg.c
Event-Calling-Function: sofia_reg_handle_register_token
Event-Calling-Line-Number: 1745
Event-Sequence: 732
profile-name: outside
to-user: 33123456
to-host: <LIBRESBC-IP>
network-ip: <FAREND-IP>
user-agent: <FAREND-UA>
profile-name: outside
network-port: 5060
registration-type: INVITE
]]