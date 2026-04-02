FROM ubuntu:22.04

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

ENV APLUS_BASE_URL="-"
