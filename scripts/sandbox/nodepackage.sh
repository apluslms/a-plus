#!/bin/bash
#
# Activates the named node packages and passes the rest for a command.
# The named package environment should be created with name-package.json and
# scripts/sandbox_available/install-node-packages.sh
#
DIR="/usr/local/nodepackages"

PDIR=$DIR/$1/node_modules
shift

# Try to activate the packages.
if [ -d $PDIR ]; then
	ln -s $PDIR .
else
	echo "Node packages environment not found ($PDIR). Trying anyway. NOT READY FOR PRODUCTION!" >&2
	echo "" >&2
	npm install
fi

$@
RESULT=$?

rm -rf node_modules

exit $RESULT
