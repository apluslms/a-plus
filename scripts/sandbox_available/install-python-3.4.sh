#!/bin/bash
#
# Installs Python 3.4 using a third party Ubuntu repository.
#
apt-add-repository -y ppa:fkrull/deadsnakes
apt-get -q update
apt-get -qy install python3.4 python3.4-dev
