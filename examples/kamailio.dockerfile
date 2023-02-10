# PLATFORM
FROM debian:buster
LABEL maintainer="Minh <hnimminh@outlook.com>"
# KAMAILIO
RUN apt-get update && apt-get install -y git gcc g++ bison flex gdb make autoconf pkg-config libssl-dev libcurl4-openssl-dev libxml2-dev libpcre3-dev python3-dev libunistring-dev libhiredis-dev curl procps lsof vim
RUN curl https://www.kamailio.org/pub/kamailio/5.4.7/src/kamailio-5.4.7_src.tar.gz -o /usr/local/src/kamailio-5.4.7_src.tar.gz
RUN tar -xzvf /usr/local/src/kamailio-5.4.7_src.tar.gz -C /usr/local/src
WORKDIR /usr/local/src/kamailio-5.4.7
RUN make include_modules="jsonrpcs ctl kex corex tm tmx outbound sl rr pv maxfwd topoh dialog usrloc registrar textops textopsx siputils sanity uac kemix auth nathelper debugger htable pike xlog app_python3 websocket regex utils tls http_client" cfg && make all && make install
RUN rm -rf /usr/local/src/kamailio* && apt-get clean && rm -rf /var/lib/apt/lists/*
ENTRYPOINT ["kamailio"]
# docker build . --file kamailio.dockerfile --platform linux/amd64 -t hnimminh/kamailio:latest
# docker push hnimminh/kamailio:latest
# docker run -it --platform linux/amd64 --entrypoint /bin/bash --name  kamproxy hnimminh/kamailio:latest
