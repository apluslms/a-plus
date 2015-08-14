#!/bin/bash
#
# Compiles all *.java files in a submission.
# --cp [class_path]
# --clean [yes to delete source files after compilation]
# Requires install-jdk-[version].sh
#
SCRIPTDIR=`dirname $0`

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
find . -maxdepth 1 -name \*.java -exec $SCRIPTDIR/_addpackagedirs.sh {} +

FILES=`find . -name \*.java`

# Compile files.
if [ "$CP" == "" ]
then
	CP=.
fi
javac -cp $CP $FILES
COMPILE_RESULT=$?

# Clean up all source files.
if args_true $CLEAN
then
	rm $FILES
fi

exit $COMPILE_RESULT
