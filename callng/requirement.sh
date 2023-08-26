#!/bin/bash
/bin/apt install -y libcurl4-openssl-dev lua-curl
/bin/ln -s /usr/include/x86_64-linux-gnu/curl /usr/include/
/usr/bin/luarocks install luaposix 35.0-1
/usr/bin/luarocks install luaredis 2.1.0-0
/usr/bin/luarocks install http 0.3-0
/usr/bin/luarocks install luasocket 3.0rc1-2
/usr/bin/luarocks install moonjson 0.1.2-1
/usr/bin/luarocks install luasec 1.2.0-1
/usr/bin/luarocks install lua-curl 0.3.13-1
