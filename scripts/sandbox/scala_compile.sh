#!/bin/bash
#
# Compiles all *.scala files in a submission.
# --cp [class_path]
# --clean [yes to delete source files after compilation]
# Requires install-scala-[version].sh
#
SCRIPTDIR=`dirname $0`

FSCPORT=30000
ARGS="-encoding utf-8 -deprecation:false -feature -language:postfixOps"
CP=
CLEAN=

# Parse arguments.
source $SCRIPTDIR/_args.sh
while args
do
	case "$ARG_ITER" in
		--cp) CP=$ARG_NEXT; args_skip ;;
		--clean) CLEAN=$ARG_NEXT; args_skip ;;
		*) ;;
	esac
done

# Fix package directories for files uploaded to root.
find . -maxdepth 1 -name \*.scala -exec $SCRIPTDIR/_addpackagedirs.sh {} +

FILES=`find . -name \*.scala`

# Compile files.
if [ "$CP" == "" ]
then
	CP=.
fi
netstat -n -l | grep -q "$FSCPORT"
if [ $? -eq 0 ]; then
	fsc -ipv4 -server localhost:$FSCPORT -classpath $CP $ARGS $FILES
else
	scalac -classpath $CP $ARGS $FILES
fi
COMPILE_RESULT=$?

# Clean up all source files.
if args_true $CLEAN
then
	rm $FILES
fi

exit $COMPILE_RESULT
