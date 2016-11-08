#!/bin/bash
#
# Looks for *-package.json files in the sandbox directories and installs
# node packages for them. The name of the package "environment" is the
# beginning part of the package description.
#
DIR=/usr/local/nodepackages

apt-get -qy install build-essential

# Check directory to store virtual environments.
mkdir -p $DIR
cd $DIR

# Create package environments.
for path in $(find /usr/local/sandbox -name \*-package.json); do
	file=${path##*/}
	name=${file%-package.json}

	if [ ! -d $name ]
	then
		mkdir $name
	fi
	cd $name
	cp $path package.json
	npm install
	cd ..
done
