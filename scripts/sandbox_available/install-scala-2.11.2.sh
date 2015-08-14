#!/bin/bash
#
# Installs Scala and places scala/scalac/scalap/fsc in path.
#
URL=http://www.scala-lang.org/files/archive/scala-2.11.2.tgz
NAME=${URL##*/}
DIR=${NAME%.tgz}

PATCH_URL=http://www.cs.hut.fi/~lehtint6/scala-2.11.2/scala-compiler.jar
PATCH_NAME=${PATCH_URL##*/}

if [ ! -f /usr/local/scala/$DIR/bin/scala ]
then

	mkdir -p /usr/local/scala
	cd /usr/local/scala/

	wget --no-check-certificate -O $NAME $URL
	tar zxvf $NAME
	rm $NAME

	wget --no-check-certificate -O $PATCH_NAME $PATCH_URL
	mv $PATCH_NAME $DIR/lib/
fi

update-alternatives --install "/usr/bin/scala" "scala" "/usr/local/scala/$DIR/bin/scala" 1
update-alternatives --install "/usr/bin/scalac" "scalac" "/usr/local/scala/$DIR/bin/scalac" 1
update-alternatives --install "/usr/bin/scalap" "scalap" "/usr/local/scala/$DIR/bin/scalap" 1
update-alternatives --install "/usr/bin/fsc" "fsc" "/usr/local/scala/$DIR/bin/fsc" 1
