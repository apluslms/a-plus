#!/bin/bash
#
# Installs Python 3.5
#
if ! [ -x /usr/bin/python3.5 ]; then
    apt-get -qy python-software-properties
    add-apt-repository -y ppa:fkrull/deadsnakes
    apt-get -q update
    apt-get -qy install python3.5 python3.5-dev
fi
if ! [ -x /usr/local/bin/pip3.5 ]; then
    wget --no-check-certificate https://bootstrap.pypa.io/get-pip.py
    python3.5 get-pip.py
    rm get-pip.py
    pip3.5 install virtualenv
fi
