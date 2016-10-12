#!/bin/bash
#
# Installs the JDK and places java/javac/javap in path.
# Due to manual download requirements the script will request
# user to download into sandbox tmp and then run manage_sandbox again.
#
NAME=jdk-8u???-linux-x64.tar.gz
DIR=jdk1.8
URL=http://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html

if [ ! -f /usr/local/jdk/$DIR/bin/java ]
then
	if [ ! -f /tmp/$NAME ]
	then
		echo "------------------------------------------------"
		echo "Oracle Java JDK has to be loaded manually!"
		echo "   $URL"
		echo "Download the latest $NAME to"
		echo "   $1/tmp/"
		echo "and run the script again."
		echo "------------------------------------------------"
		exit 1
	fi

	mkdir -p /usr/local/jdk
	cd /usr/local/jdk

	tar zxvf /tmp/$NAME
	mv $DIR* $DIR

	rm /tmp/$NAME
fi

# Keeping to old ways and using shell scripts to force some java options.
# Should it be better to include these in exercise configuration when really needed.
echo "#!/bin/bash" > /usr/local/jdk/$DIR/java.sh
#echo "/usr/local/jdk/$DIR/bin/java -Xms16m -Xmx512m -Djava.security.manager -Djava.security.policy=/usr/local/sandbox/policy.java \$@" >> /usr/local/jdk/$DIR/java.sh
echo "/usr/local/jdk/$DIR/bin/java -XX:+UseSerialGC -Xms16m -Xmx512m \$@" >> /usr/local/jdk/$DIR/java.sh
echo "#!/bin/bash" > /usr/local/jdk/$DIR/javac.sh
#echo "/usr/local/jdk/$DIR/bin/javac -J-Xms16m -J-Xmx128m -encoding latin1 \$@" >> /usr/local/jdk/$DIR/javac.sh
echo "/usr/local/jdk/$DIR/bin/javac -J-Xms16m -J-Xmx128m \$@" >> /usr/local/jdk/$DIR/javac.sh
chmod a+x /usr/local/jdk/$DIR/java.sh /usr/local/jdk/$DIR/javac.sh

update-alternatives --install "/usr/bin/java" "java" "/usr/local/jdk/$DIR/java.sh" 1
update-alternatives --install "/usr/bin/javac" "javac" "/usr/local/jdk/$DIR/javac.sh" 1
update-alternatives --install "/usr/bin/javap" "javap" "/usr/local/jdk/$DIR/bin/javap" 1
