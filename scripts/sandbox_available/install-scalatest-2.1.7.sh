#!/bin/bash
#
# Provides library for scala. Exercise can add it to classpath.
#   scala_compile.sh --cp .:/usr/local/scala/libs/scalatest_2.11-2.1.7.jar
#
URL=https://oss.sonatype.org/content/groups/public/org/scalatest/scalatest_2.11/2.1.7/scalatest_2.11-2.1.7.jar
NAME=${URL##*/}

apt-get -qy install libxtst6

if [ ! -f /usr/local/scala/libs/$NAME ]
then

	mkdir -p /usr/local/scala/libs
	cd /usr/local/scala/libs/

	wget --no-check-certificate -O $NAME $URL
fi
