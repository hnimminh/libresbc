!#/bin/bash
#------------------------------------------------------------------------------------------------------------
#                   LUA LANGUAGE
#       lua-lang: https://www.lua.org/
#       luarocks: https://luarocks.org/
#------------------------------------------------------------------------------------------------------------
app-get install -y liblua5.2-dev lua5.2 
app-get install -y luarocks
/usr/bin/luarocks install luaposix 35.0-1
/usr/bin/luarocks install luaredis 2.0.5-2
/usr/bin/luarocks install http 0.3-0
/usr/bin/luarocks install luasocket 3.0rc1-2
/usr/bin/luarocks install moonjson 0.1.2-1
/usr/bin/luarocks install lua_uuid 0.2.0-2
#------------------------------------------------------------------------------------------------------------
#                   FREESWITCH: 
#       code: https://github.com/signalwire/freeswitch
#       wiki: https://freeswitch.org/confluence/
#------------------------------------------------------------------------------------------------------------
cd /usr/local/src
apt-get update && apt-get install -yq gnupg2 wget lsb-release
wget -O - https://files.freeswitch.org/repo/deb/debian-release/fsstretch-archive-keyring.asc | apt-key add -
echo "deb http://files.freeswitch.org/repo/deb/debian-release/ `lsb_release -sc` main" > /etc/apt/sources.list.d/freeswitch.list
echo "deb-src http://files.freeswitch.org/repo/deb/debian-release/ `lsb_release -sc` main" >> /etc/apt/sources.list.d/freeswitch.list
apt-get update

# Install dependencies required for the build
# apt-get install -y g++ g++-8 gcc gcc-8 autoconf automake libtool wget libncurses-dev zlib1g-dev libcurl3-gnutls libcurl4-openssl-dev libgnutls-openssl27 libpcre16-3 libpcre3-dev libpcre32-3 libpcrecpp0v5 libspeex-dev libspeex1 libspeexdsp-dev libspeexdsp1 libldns-dev libldns2 libedit-dev libspeex-dev libspeex1 libspeexdsp-dev libspeexdsp1 libsqlite3-dev libssl-dev yasm libsndfile1 libsndfile1-dev libvpx5 libopus-dev libopus0 libopusfile-dev libopusfile0
apt-get build-dep freeswitch

wget https://files.freeswitch.org/freeswitch-releases/freeswitch-1.10.5.-release.tar.gz -O freeswitch-1.10.5.-release.tar.gz 
tar -xzvf freeswitch-1.10.5.-release.tar.gz
cd freeswitch-1.10.5.-release
mv modules.conf modules.conf.origin
cat >modules.conf<< EOF 
applications/mod_commands
applications/mod_dptools
applications/mod_distributor
dialplans/mod_dialplan_xml
endpoints/mod_sofia
event_handlers/mod_event_socket
languages/mod_python
languages/mod_lua
loggers/mod_console
loggers/mod_logfile
applications/mod_spandsp
#event_handlers/mod_snmp
formats/mod_sndfile
xml_int/mod_xml_rpc
xml_int/mod_xml_curl
EOF

./configure -C --prefix=/usr/local --with-rundir=/var/run/ --with-logfiledir=/var/log/freeswitch/ --enable-64 --with-openssl
make
make install
mv /usr/local/etc/freeswitch /usr/local/etc/freeswitch.origin
#-------------------------- FreeSWITCH configuration --------------------------
#
#  Locations:
#
#      prefix:          /usr/local
#      exec_prefix:     /usr/local
#      bindir:          ${exec_prefix}/bin
#      confdir:         /usr/local/etc/freeswitch
#      libdir:          /usr/local/lib
#      datadir:         /usr/local/share/freeswitch
#      localstatedir:   /usr/local/var/lib/freeswitch
#      includedir:      /usr/local/include/freeswitch
#
#      certsdir:        /usr/local/etc/freeswitch/tls
#      dbdir:           /usr/local/var/lib/freeswitch/db
#      grammardir:      /usr/local/share/freeswitch/grammar
#      htdocsdir:       /usr/local/share/freeswitch/htdocs
#      fontsdir:        /usr/local/share/freeswitch/fonts
#      logfiledir:      /var/log/freeswitch/
#      modulesdir:      /usr/local/lib/freeswitch/mod
#      pkgconfigdir:    /usr/local/lib/pkgconfig
#      recordingsdir:   /usr/local/var/lib/freeswitch/recordings
#      imagesdir:       /usr/local/var/lib/freeswitch/images
#      runtimedir:      /var/run/
#      scriptdir:       /usr/local/share/freeswitch/scripts
#      soundsdir:       /usr/local/share/freeswitch/sounds
#      storagedir:      /usr/local/var/lib/freeswitch/storage
#      cachedir:        /usr/local/var/cache/freeswitch
#
#------------------------------------------------------------------------------------------------------------
#                   G729 CODEC: 
#       https://github.com/xadhoom/mod_bcg729, 
#       https://github.com/BelledonneCommunications/bcg729
#------------------------------------------------------------------------------------------------------------
cd /usr/local/src
git clone https://github.com/xadhoom/mod_bcg729.git
cd mod_bcg729
sed -i 's/^FS_INCLUDES=.*/FS_INCLUDES=\/usr\/local\/include\/freeswitch/' Makefile
sed -i 's/^FS_MODULES=.*/FS_MODULES=\/usr\/local\/lib\/freeswitch\/mod/' Makefile
make
make install
#------------------------------------------------------------------------------------------------------------
#                   PYTHON3
#------------------------------------------------------------------------------------------------------------
apt-get install -y python3 python3-dev python3-pip
#------------------------------------------------------------------------------------------------------------
#                   NGINX
#------------------------------------------------------------------------------------------------------------
apt-get install -y nginx
mv /etc/nginx /etc/nginx.origin
#------------------------------------------------------------------------------------------------------------
#                   CAPTAGENT: 
#       https://github.com/sipcapture/captagent
#------------------------------------------------------------------------------------------------------------
cd /usr/local/src
apt-get install libexpat-dev libpcap-dev libjson-c-dev libtool automake flex bison libgcrypt-dev libuv1-dev libpcre3-dev libfl-dev
wget https://github.com/sipcapture/captagent/archive/6.3.1.tar.gz -O captagent-6.3.1.tar.gz
tar -xzvf captagent-6.3.1.tar.gz
cd captagent-6.3.1
./build.sh
./configure --enable-compression --enable-ipv6 --enable-pcre --enable-ssl --enable-tls
make
make install
mv /usr/local/captagent/etc/captagent /usr/local/captagent/etc/captagent.origin
#------------------------------------------------------------------------------------------------------------
#                   REDIS
#------------------------------------------------------------------------------------------------------------
apt-get install redis-server
systemctl enable redis-server
#------------------------------------------------------------------------------------------------------------
#                   NETFILTER
#------------------------------------------------------------------------------------------------------------
apt-get install ipset iptables
ipset create rtppeers hash:net family inet hashsize 1024 maxelem 65536 -exist
ipset create sippeers hash:net family inet hashsize 1024 maxelem 65536 -exist
#------------------------------------------------------------------------------------------------------------
#                   LIBRESBC
#------------------------------------------------------------------------------------------------------------
mkdir -p /var/log/libresbc/cdr
mkdir -p /usr/libresbc/versions
ln -snf /usr/local/bin/fs_cli /usr/bin/fscli