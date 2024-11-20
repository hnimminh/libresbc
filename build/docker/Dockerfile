FROM debian:bullseye AS build
LABEL maintainer="Minh Minh <hnimminh@outlook.com>"

# ==================== BUILD ====================

# BASE SOFTWARE
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get -yq install \
# base
    git curl wget \
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
    libavformat-dev libswscale-dev libavresample-dev libpq-dev\
    libsndfile1-dev libflac-dev libogg-dev libvorbis-dev flite1-dev \
# kams
    flex gdb libxml2-dev libunistring-dev libhiredis-dev

# Download FreeSWITCH & add modules
RUN git clone https://github.com/signalwire/libks /usr/src/libs/libks && \
    git clone --branch v1.13.17 https://github.com/freeswitch/sofia-sip.git /usr/src/libs/sofia-sip && \
    git clone https://github.com/freeswitch/spandsp /usr/src/libs/spandsp && \
    git clone https://github.com/signalwire/signalwire-c /usr/src/libs/signalwire-c && \
    git clone --branch v1.10.11-libre-a https://github.com/hnimminh/freeswitch.git /usr/src/freeswitch && \
    cp /usr/include/opencore-amrwb/dec_if.h /usr/src/freeswitch/src/mod/codecs/mod_amrwb/dec_if.h && \
    cp /usr/include/vo-amrwbenc/enc_if.h /usr/src/freeswitch/src/mod/codecs/mod_amrwb/enc_if.h && \
    cp /usr/include/opencore-amrnb/interf_enc.h /usr/src/freeswitch/src/mod/codecs/mod_amr/interf_enc.h && \
    cp /usr/include/opencore-amrnb/interf_dec.h /usr/src/freeswitch/src/mod/codecs/mod_amr/interf_dec.h

# Build FreeSWITCH
RUN cd /usr/src/libs/libks && cmake . -DCMAKE_INSTALL_PREFIX=/usr -DWITH_LIBBACKTRACE=1 && make install
RUN cd /usr/src/libs/sofia-sip && ./bootstrap.sh && ./configure CFLAGS="-g -ggdb" --with-pic --with-glib=no --without-doxygen --disable-stun --prefix=/usr && make -j`nproc --all` && make install
RUN cd /usr/src/libs/spandsp && git checkout 0d2e6ac && ./bootstrap.sh && ./configure CFLAGS="-g -ggdb" --with-pic --prefix=/usr && make -j`nproc --all` && make install
RUN cd /usr/src/libs/signalwire-c && PKG_CONFIG_PATH=/usr/lib/pkgconfig cmake . -DCMAKE_INSTALL_PREFIX=/usr && make install
RUN --mount=type=bind,source=build/ansible/roles/platform/files/modules.conf,target=/usr/src/freeswitch/modules.conf \
    cd /usr/src/freeswitch && ./bootstrap.sh -j && ./configure -C --prefix=/usr/local --with-rundir=/run/freeswitch --with-logfiledir=/var/log/freeswitch/ --enable-64 --with-openssl && make -j`nproc` && make install

# Download and build G729 codec module
RUN git clone https://github.com/hnimminh/mod_bcg729.git /usr/local/src/mod_bcg729 && cd /usr/local/src/mod_bcg729 && make && make install

# Download and build Kamailio
RUN curl https://www.kamailio.org/pub/kamailio/5.7.1/src/kamailio-5.7.1_src.tar.gz -o /usr/local/src/kamailio-5.7.1_src.tar.gz && \
    tar -xzvf /usr/local/src/kamailio-5.7.1_src.tar.gz -C /usr/local/src
RUN cd /usr/local/src/kamailio-5.7.1 && \
    make cfg && make include_modules="jsonrpcs ctl kex corex tm tmx outbound sl rr pv maxfwd topoh dialog usrloc registrar textops textopsx siputils sanity uac kemix auth nathelper tls debugger htable pike xlog app_lua regex utils" cfg && \
    make all && make install

# Install LUA & Python requirements
RUN --mount=type=bind,rw,source=callng/requirement.sh,target=/opt/libresbc/callng/requirement.sh \
    chmod +x /opt/libresbc/callng/requirement.sh && /opt/libresbc/callng/requirement.sh
RUN --mount=type=bind,source=liberator/requirements.txt,target=/opt/libresbc/liberator/requirements.txt \
    pip3 install -r /opt/libresbc/liberator/requirements.txt

# Install Go
RUN curl -L https://go.dev/dl/go1.23.2.linux-amd64.tar.gz -o /usr/local/go1.23.2.linux-amd64.tar.gz && tar -xzf /usr/local/go1.23.2.linux-amd64.tar.gz -C /usr/local

# Build LibreSBC WebUI
COPY ./webui /opt/libresbc/webui
RUN cd /opt/libresbc/webui && /usr/local/go/bin/go build -o /opt/libresbc/webui/webuisrv


# ==================== RUNTIME ====================

FROM debian:bullseye-slim
LABEL maintainer="Minh Minh <hnimminh@outlook.com>"
ENV LIBRE_CONTAINERIZED 1
ENV LIBRE_BUILTIN_FIREWALL 0
ENV LIBRE_REDIS 1

# Install runtime packages
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get -yq --no-install-recommends --no-install-suggests install \
    lsof vim redis procps sngrep tcpdump net-tools iproute2 curl \
    python3 lua5.2 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy files from build stage
COPY --from=build /usr/lib/x86_64-linux-gnu	     /usr/lib/x86_64-linux-gnu
COPY --from=build /usr/lib/lib*			        /usr/lib/
COPY --from=build /usr/local/bin		        /usr/local/bin
COPY --from=build /usr/local/lib/freeswitch	    /usr/local/lib/freeswitch
COPY --from=build /usr/local/var/lib/freeswitch	/usr/local/var/lib/freeswitch
COPY --from=build /usr/local/share/freeswitch	/usr/local/share/freeswitch
COPY --from=build /usr/local/etc/freeswitch 	/usr/local/etc/freeswitch
COPY --from=build /usr/local/lib/lib*		    /usr/local/lib/
COPY --from=build /usr/local/sbin/kam*		    /usr/local/sbin/
COPY --from=build /usr/local/share/kamailio	    /usr/local/share/kamailio
COPY --from=build /usr/local/etc/kamailio	    /usr/local/etc/kamailio
COPY --from=build /usr/local/lib64/kamailio	    /usr/local/lib64/kamailio
COPY --from=build /usr/local/lib/lua		    /usr/local/lib/lua
COPY --from=build /usr/local/share/lua		    /usr/local/share/lua
COPY --from=build /usr/local/lib/python3.9	    /usr/local/lib/python3.9
COPY --from=build /opt/libresbc/webui		    /opt/libresbc/webui

COPY ./callng		/opt/libresbc/callng
COPY ./liberator	/opt/libresbc/liberator

# LAYOUT
RUN mkdir -p /run/redis /var/log/libresbc/cdr && \
    ln -nfs /opt/libresbc/callng /usr/local/share/lua/5.2/callng && \
    ln -nfs /opt/libresbc/callng /usr/local/share/freeswitch/scripts/callng

VOLUME ["/var/redis", "/var/tls"]
WORKDIR /opt/libresbc/liberator
CMD ["/usr/bin/python3", "/opt/libresbc/liberator/main.py"]

# docker build --platform linux/amd64 -t hnimminh/libresbc:latest -f build/docker/Dockerfile .
# docker tag hnimminh/libresbc:latest hnimminh/libresbc:0.7.1.c
# docker run --env-file build/docker/libre.env --cap-add NET_ADMIN --cap-add SYS_NICE --network host --name libresbc -volume libresbc:/var/redis --volume libresbc:/var/tls hnimminh/libresbc:latest
