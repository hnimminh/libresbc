FROM docker.com/libresbc
RUN rm -rf /usr/libresbc
ADD . /libresbc
RUN apt-get update -y
RUN apt-get install -y build-essential libmysqlclient-dev python-pip python-dev
RUN pip install --upgrade pip
RUN pip install -r requirements.txt