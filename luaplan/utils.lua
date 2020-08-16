
function logger(msg)
    local log = require("posix.syslog")
    log.openlog('libresbc', log.LOG_PID, log.LOG_LOCAL6)
    log.syslog(log.LOG_INFO, msg)
    log.closelog()
end
