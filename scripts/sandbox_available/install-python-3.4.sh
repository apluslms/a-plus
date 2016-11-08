#!/bin/bash
#
# Installs Python 3.4
#
if ! [ -x /usr/bin/python3.4 ]; then
    apt-get -qy install python-software-properties
    add-apt-repository -y ppa:fkrull/deadsnakes
    apt-get -q update
    apt-get -qy install python3.4 python3.4-dev
fi
if ! [ -x /usr/local/bin/pip3.4 ]; then
    wget --no-check-certificate https://bootstrap.pypa.io/get-pip.py
    python3.4 get-pip.py
    rm get-pip.py
    pip3.4 install virtualenv
fi

update-alternatives --install "/usr/bin/python3" "python3" "/usr/bin/python3.4" 1
