# PLATFORM
FROM debian:buster
LABEL maintainer="Minh <hnimminh@outlook.com>"
# RTPENGINE
RUN apt-get update \
  && apt-get -y --quiet --force-yes upgrade curl iproute2 \
  && apt-get install -y --no-install-recommends ca-certificates gcc g++ make build-essential git iptables-dev libavfilter-dev \
  libevent-dev libpcap-dev libxmlrpc-core-c3-dev markdown \
  libjson-glib-dev default-libmysqlclient-dev libhiredis-dev libssl-dev \
  libcurl4-openssl-dev libavcodec-extra gperf libspandsp-dev libwebsockets-dev libopus-dev
RUN cd /usr/local/src \
  && git clone https://github.com/sipwise/rtpengine.git \
  && cd rtpengine/daemon \
  && make && make install \
  && cp /usr/local/src/rtpengine/daemon/rtpengine /usr/local/bin/rtpengine \
  && rm -Rf /usr/local/src/rtpengine \
  && mkdir /etc/rtpengine /opt/dyscavo
RUN apt-get purge -y --quiet --force-yes --auto-remove \
  ca-certificates gcc g++ make build-essential git markdown \
  && rm -rf /var/lib/apt/* \
  && rm -rf /var/lib/dpkg/* \
  && rm -rf /var/lib/cache/* \
  && rm -Rf /var/log/* \
  && rm -Rf /usr/local/src/* \
  && rm -Rf /var/lib/apt/lists/*
ENTRYPOINT ["rtpengine"]
# docker build . --file rtpengine.dockerfile --platform linux/amd64 -t hnimminh/rtpengine:latest
# docker push hnimminh/rtpengine:latest
# docker run -it --platform linux/amd64 --entrypoint /bin/bash --name  rtpengine hnimminh/rtpengine:latest
