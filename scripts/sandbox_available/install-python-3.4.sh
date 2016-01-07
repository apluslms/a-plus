#!/bin/bash
#
# Installs Python 3.4.
#
if ! [ -x /usr/bin/python3.4 ]; then
    apt-get -qy python-software-properties
    add-apt-repository ppa:fkrull/deadsnakes
    apt-get -q update
    apt-get -qy install python3.4 python3.4-dev
fi
python3.4 -m ensurepip
python3.4 -m pip install virtualenv
