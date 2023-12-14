FROM debian:bullseye
LABEL maintainer="Minh Minh <hnimminh@outlook.com>"
ENV LIBRE_CONTAINERIZED 1
ENV LIBRE_BUILTIN_FIREWALL 0
ENV LIBRE_REDIS 1

# BASE SOFTWARE
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get -yq install \
# base
    git curl wget lsof vim redis procps\
    sngrep tcpdump net-tools rsyslog logrotate rsync nftables chrony \
# build
    build-essential make cmake gnupg2 automake autoconf g++ gcc 'libtool-bin|libtool' pkg-config \
# general
    libssl-dev zlib1g-dev libdb-dev unixodbc-dev libncurses5-dev libexpat1-dev libgdbm-dev bison erlang-dev libtpl-dev libtiff5-dev uuid-dev \
# core
    libpcre3-dev libedit-dev libsqlite3-dev libcurl4-openssl-dev openssl libcrypto++8 nasm\
# codecs
    libogg-dev libspeex-dev libspeexdsp-dev libopus-dev libopencore-amrwb-dev libopencore-amrwb0 \
    libvo-amrwbenc-dev libvo-amrwbenc0  libopencore-amrnb-dev libopencore-amrnb0 \
# languages
    python3 python3-dev python3-pip python-setuptools liblua5.2-dev lua5.2 luarocks lua-curl\
# mods
    libavformat-dev libswscale-dev libavresample-dev \
    libsndfile1-dev libflac-dev libogg-dev libvorbis-dev flite1-dev \
# kams
    flex gdb libxml2-dev libunistring-dev libhiredis-dev

RUN mkdir -p /run/redis /opt/libresbc /var/log/libresbc/cdr
COPY callng /opt/libresbc/callng
COPY liberator /opt/libresbc/liberator
COPY build/ansible/roles/platform/files/modules.conf /opt/libresbc/modules.conf

# FREESWITCH
RUN git clone https://github.com/signalwire/libks /usr/src/libs/libks && \
    git clone --branch v1.13.15 https://github.com/freeswitch/sofia-sip.git /usr/src/libs/sofia-sip && \
    git clone https://github.com/freeswitch/spandsp /usr/src/libs/spandsp && \
    git clone https://github.com/signalwire/signalwire-c /usr/src/libs/signalwire-c && \
    git clone --branch v1.10.9 https://github.com/signalwire/freeswitch.git /usr/src/freeswitch && \
    cp /usr/include/opencore-amrwb/dec_if.h /usr/src/freeswitch/src/mod/codecs/mod_amrwb/dec_if.h && \
    cp /usr/include/vo-amrwbenc/enc_if.h /usr/src/freeswitch/src/mod/codecs/mod_amrwb/enc_if.h && \
    cp /usr/include/opencore-amrnb/interf_enc.h /usr/src/freeswitch/src/mod/codecs/mod_amr/interf_enc.h && \
    cp /usr/include/opencore-amrnb/interf_dec.h /usr/src/freeswitch/src/mod/codecs/mod_amr/interf_dec.h

RUN cd /usr/src/libs/libks && cmake . -DCMAKE_INSTALL_PREFIX=/usr -DWITH_LIBBACKTRACE=1 && make install && \
    cd /usr/src/libs/sofia-sip && ./bootstrap.sh && ./configure CFLAGS="-g -ggdb" --with-pic --with-glib=no --without-doxygen --disable-stun --prefix=/usr && make -j`nproc --all` && make install && \
    cd /usr/src/libs/spandsp && git checkout 0d2e6ac && ./bootstrap.sh && ./configure CFLAGS="-g -ggdb" --with-pic --prefix=/usr && make -j`nproc --all` && make install && \
    cd /usr/src/libs/signalwire-c && PKG_CONFIG_PATH=/usr/lib/pkgconfig cmake . -DCMAKE_INSTALL_PREFIX=/usr && make install && \
    cd /usr/src/freeswitch && cp /opt/libresbc/modules.conf /usr/src/freeswitch/modules.conf && \
    ./bootstrap.sh -j && ./configure -C --prefix=/usr/local --with-rundir=/run/freeswitch --with-logfiledir=/var/log/freeswitch/ --enable-64 --with-openssl && make -j`nproc` && make install

RUN git clone https://github.com/hnimminh/mod_bcg729.git /usr/local/src/mod_bcg729 && cd /usr/local/src/mod_bcg729 && make && make install

# KAMAILIO
RUN curl https://www.kamailio.org/pub/kamailio/5.7.1/src/kamailio-5.7.1_src.tar.gz -o /usr/local/src/kamailio-5.7.1_src.tar.gz && \
    tar -xzvf /usr/local/src/kamailio-5.7.1_src.tar.gz -C /usr/local/src && cd /usr/local/src/kamailio-5.7.1 && \
    make cfg && make include_modules="jsonrpcs ctl kex corex tm tmx outbound sl rr pv maxfwd topoh dialog usrloc registrar textops textopsx siputils sanity uac kemix auth nathelper tls debugger htable pike xlog app_lua regex utils" cfg && \
    make all && make install

RUN chmod +x /opt/libresbc/callng/requirement.sh && /opt/libresbc/callng/requirement.sh &&\
    pip3 install -r /opt/libresbc/liberator/requirements.txt

# LAYOUT & CLEANUP
RUN rm -rf /usr/src/freeswitch-1.10.9.tar.gz /usr/local/freeswitch/conf/* /usr/local/src/kamailio* && \
    apt-get clean && rm -rf /var/lib/apt/lists/* && \
    ln -nfs /opt/libresbc/callng /usr/local/share/lua/5.2/callng && \
    ln -nfs /opt/libresbc/callng /usr/local/share/freeswitch/scripts/callng

WORKDIR /opt/libresbc/liberator
CMD ["/usr/bin/python3", "/opt/libresbc/liberator/main.py"]

# docker build --platform linux/amd64 -t hnimminh/libresbc:latest -f build/docker/Dockerfile .
# docker run --env-file ../libre.env --cap-add NET_ADMIN --cap-add SYS_NICE --network host --name libresbc hnimminh/libresbc:latest
