dofile("/usr/libresbc/run/luaplan/utils.lua")

if ( session:ready() ) then
    -- answer the call
    session:answer()
    context = session:getVariable("context")
    direction = session:getVariable("direction")
    sip_req_user = session:getVariable("sip_req_user");
    destination_number = session:getVariable("destination_number");
    sip_from_display = session:getVariable("sip_from_display")
    sip_from_user = session:getVariable("sip_from_user")
    sip_network_ip = session:getVariable("sip_network_ip")
    sip_to_host = session:getVariable("sip_to_host")
    sofia_profile_name = session:getVariable("sofia_profile_name")
    uuid = session:getVariable("uuid")

    caller_id_name = session:getVariable("caller_id_name")
    caller_id_number = session:getVariable("caller_id_number")
    effective_caller_id_name = session:getVariable("effective_caller_id_name")
    effective_caller_id_number = session:getVariable("effective_caller_id_number")


    voicelog(string.format(" module=luaplan, uuid=%s, context=%s, direction=%s, sofia_profile_name=%s, caller_id_name=%s, caller_id_number=%s, effective_caller_id_name=%s, effective_caller_id_number=%s,   sip_req_user=%s, destination_number=%s, sip_from_display=%s, sip_from_user=%s, sip_network_ip=%sm, sip_to_host=%s", uuid, context, direction, sofia_profile_name, caller_id_name, caller_id_number, effective_caller_id_name, effective_caller_id_number, sip_req_user, destination_number, fstr(sip_from_display), sip_from_user, sip_network_ip, sip_to_host))

    -- play music
    session:execute("playback","/tmp/ulaw08m.wav")
    -- hangup session
    session:hangup()
end 