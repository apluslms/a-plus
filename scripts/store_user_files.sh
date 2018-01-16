#!/bin/bash
#
# Copies files from the (temporary) submission directory to the permanent
# personal directory of the user.

cd `dirname $0`/..
source scripts/_config.sh
source scripts/_copy_util.sh

DIR=
TARGETDIR=
CP=

# Parse arguments.
source scripts/sandbox/_args.sh
while args; do
	case "$ARG_ITER" in
		--dir) DIR=$ARG_NEXT; args_skip ;;
		--cp) CP=$ARG_NEXT; args_skip ;;
		--target) TARGETDIR=$ARG_NEXT; args_skip ;;
		*) ;;
	esac
done
args_require_dir --dir $DIR
args_require_dir --target $TARGETDIR


# Prepare to travel path->path lists.

list=($CP)
copy_paths $DIR/ $TARGETDIR/
