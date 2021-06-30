FROM ubuntu:latest

ARG GECKODRIVER_FILE=geckodriver-v0.29.1-linux64.tar.gz
ARG GECKODRIVER_LINK=https://github.com/mozilla/geckodriver/releases/download/v0.29.1/$GECKODRIVER_FILE

ENV DEBIAN_FRONTEND=noninteractive

RUN apt update -y
RUN apt install -y python3 python3-pip git gettext curl firefox
RUN pip3 install --upgrade pip setuptools wheel

# install python requirements
COPY requirements.txt requirements.txt
COPY requirements_testing.txt requirements_testing.txt
RUN pip install -r requirements.txt
RUN pip install -r requirements_testing.txt
RUN rm requirements.txt requirements_testing.txt

# install geckodriver for selenium
RUN curl -s -L $GECKODRIVER_LINK | tar -xz
RUN chmod +x geckodriver
RUN mv geckodriver /usr/bin/

ENV APLUS_BASE_URL="-"
