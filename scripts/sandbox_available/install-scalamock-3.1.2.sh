#!/bin/bash
#
# Provides library for scala. Exercise can add it to classpath.
#   scala_compile.sh --cp .:/usr/local/scala/libs/scalatest_2.11-2.1.7.jar:/usr/local/scala/libs/scalamock-core_2.11-3.1.2.jar:/usr/local/scala/libs/scalamock-scalatest-support_2.11-3.1.2.jar
#
URL=https://oss.sonatype.org/content/repositories/releases/org/scalamock/scalamock-core_2.11/3.1.2/scalamock-core_2.11-3.1.2.jar
URL2=https://oss.sonatype.org/content/repositories/releases/org/scalamock/scalamock-scalatest-support_2.11/3.1.2/scalamock-scalatest-support_2.11-3.1.2.jar
NAME=${URL##*/}
NAME2=${URL2##*/}

mkdir -p /usr/local/scala/libs
cd /usr/local/scala/libs/
if [ ! -f $NAME ]
then
	wget --no-check-certificate -O $NAME $URL
fi
if [ ! -f $NAME2 ]
then
	wget --no-check-certificate -O $NAME2 $URL2
fi
