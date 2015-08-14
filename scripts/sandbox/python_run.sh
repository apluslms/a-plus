#!/bin/bash
#
# Passes the call for python interpreter but can handle extra option:
# --virtualenv [name]
# The named virtualenv is required to setup via install-python-* scripts.
#
SCRIPTDIR=`dirname $0`
VDIR="/usr/local/pyvirtualenvs"

VENV=
ARGS=""

# Parse arguments.
source $SCRIPTDIR/_args.sh
while args
do
	case "$ARG_ITER" in
		--virtualenv) VENV=$ARG_NEXT; args_skip ;;
		*) ARGS="$ARGS $ARG_ITER" ;;
	esac
done

# Activate virtualenv if set.
if [ "$VENV" != "" ]
then
	source $VDIR/$VENV/bin/activate
fi

python$ARGS
RESULT=$?

if [ "$VENV" != "" ]
then
	deactivate
fi

exit $RESULT
