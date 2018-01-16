#!/bin/bash
#
# Provides firefox browser for in browser testing.
# Tests are recommended to run with python using selenium.webdriver.Firefox()
# The selenium can be installed with pip inside a virtualenv.
#
if ! grep --quiet universe /etc/apt/sources.list
then
	echo "deb http://archive.ubuntu.com/ubuntu precise universe restricted" >> /etc/apt/sources.list
fi
if ! grep --quiet precise-security /etc/apt/sources.list
then
	echo "deb http://archive.ubuntu.com/ubuntu precise-security main universe restricted" >> /etc/apt/sources.list
fi
apt-get -q update
apt-get -qy install firefox dbus-x11

if [ ! -f /usr/local/geckodriver ]
then
	wget --no-check-certificate -O tmp.tar.gz https://github.com/mozilla/geckodriver/releases/download/v0.11.1/geckodriver-v0.11.1-linux64.tar.gz
	tar zxvf tmp.tar.gz
	rm tmp.tar.gz
	mv geckodriver /usr/local/geckodriver
fi
