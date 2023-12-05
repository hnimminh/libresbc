--
-- callng:privision.lua
--
-- The Initial Developer of the Original Code is
-- Minh Minh <hnimminh at[@] outlook dot[.] com>
-- Portions created by the Initial Developer are Copyright (C) the Initial Developer.
-- All Rights Reserved.
--

require("callng.utilities")
---------------------------------------------------------------------------

XMLAPIMAP = {
    ["distributor.conf"]        = "distributor",
    ["acl.conf"]                = "acl",
    ["sofia.conf"]              = "sip-setting",
    ["post_load_switch.conf"]   = "switch",
}


function provisioner()
    local section = XML_REQUEST.section
    local keyvalue = XML_REQUEST.key_value

    local subject
    if section == "configuration" then
        subject = XMLAPIMAP[keyvalue]
    elseif section == "directory" then
        subject = "directory"
    else
        return
    end
    log.info('module=callng, space=provisioner, action=inspect, section=%s, subject=%s', section, subject)

    if subject then
        local ok, err, body, status = curlget(LIBERATOR_CFGAPI_URL..'/'..subject, {["x-nodeid"] = NODEID})
        if not ok or status~=200 then
            log.error('module=callng, space=provisioner, action=request, subject=%s, error=%s', subject, err)
            return
        end

        log.debug('module=callng, space=provisioner, action=request, subject=%s, \n%s', subject, body)
        if body then
            XML_STRING = body
        end
    end
end

---------------------******************************---------------------
---------------------*****|       MAIN       |*****---------------------
---------------------******************************---------------------
local result, error = pcall(provisioner)
if not result then
    logger("module=callng, space=provisioner, action=exception, error=%s", error)
end
