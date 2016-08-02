#!/bin/bash
#
# Installs Scala and places scala/scalac/scalap/fsc in path.
#
URL=http://downloads.lightbend.com/scala/2.11.8/scala-2.11.8.tgz
NAME=${URL##*/}
DIR=${NAME%.tgz}

if [ ! -f /usr/local/scala/$DIR/bin/scala ]
then

	mkdir -p /usr/local/scala
	cd /usr/local/scala/

	wget --no-check-certificate -O $NAME $URL
	tar xvf $NAME
	rm $NAME
fi

update-alternatives --install "/usr/bin/scala" "scala" "/usr/local/scala/$DIR/bin/scala" 1
update-alternatives --install "/usr/bin/scalac" "scalac" "/usr/local/scala/$DIR/bin/scalac" 1
update-alternatives --install "/usr/bin/scalap" "scalap" "/usr/local/scala/$DIR/bin/scalap" 1
update-alternatives --install "/usr/bin/fsc" "fsc" "/usr/local/scala/$DIR/bin/fsc" 1
