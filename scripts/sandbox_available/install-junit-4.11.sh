#!/bin/bash
#
# Provides library for java. Exercise can add it to classpath.
#   java_compile.sh --cp .:/usr/local/jdk/libs/junit-4.11.jar
#
URL=http://search.maven.org/remotecontent?filepath=junit/junit/4.11/junit-4.11.jar
NAME=${URL##*/}

if [ ! -f /usr/local/jdk/libs/$NAME ]
then

	mkdir -p /usr/local/jdk/libs
	cd /usr/local/jdk/libs/

	wget --no-check-certificate -O $NAME $URL
fi
