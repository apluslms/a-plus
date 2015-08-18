#!/bin/bash
#
# Installs nodejs using a third party Ubuntu repository.
#
if ! [ -x /usr/bin/nodejs ]; then
	apt-get -qy install python-software-properties
	apt-add-repository -y ppa:chris-lea/node.js
	if ! grep --quiet universe /etc/apt/sources.list
	then
		echo "deb http://archive.ubuntu.com/ubuntu precise universe restricted" >> /etc/apt/sources.list
	fi
	if ! grep --quiet precise-security /etc/apt/sources.list
	then
		echo "deb http://archive.ubuntu.com/ubuntu precise-security main universe restricted" >> /etc/apt/sources.list
	fi
	apt-get -q update
	apt-get -qy install nodejs
fi
