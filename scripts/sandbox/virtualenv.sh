#!/bin/bash
#
# Activates the named Python virtualenv and passes the rest for a command.
# The named virtualenv should be created with name-requirements.txt and
# scripts/sandbox_available/install-python-virtualenvs.sh
#
VDIR="/usr/local/pyvirtualenvs"

VENV=VDIR/$1/bin/activate
shift

# Try to activate the virtualenv.
if [ -f $VENV ]; then
	source $VENV
	$@
	RESULT=$?
	deactivate
else
	echo "Virtual environment not found. Trying anyway. NOT READY FOR PRODUCTION!" >&2
	echo "" >&2
	$@
	RESULT=$?
fi
exit $RESULT
