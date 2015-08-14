#!/bin/bash
cd `dirname $0`/..
source scripts/_config.sh

UNZIP_ATTACHMENT=
DIR=
CHARSET=
ADD=
UNZIP=
PULL=

# Parse arguments.
source scripts/sandbox/_args.sh
while args
do
	case "$ARG_ITER" in
		--attachment) UNZIP_ATTACHMENT=$ARG_NEXT; args_skip ;;
		--dir) DIR=$ARG_NEXT; args_skip ;;
		--charset) CHARSET=$ARG_NEXT; args_skip ;;
		--add) ADD=$ARG_NEXT; args_skip ;;
		--unzip) UNZIP=$ARG_NEXT; args_skip ;;
		--pull) PULL=$ARG_NEXT; args_skip ;;
		*) ;;
	esac
done
args_require_dir --dir $DIR

cd $DIR

# Check and unzip attached exercise.
if [ "$UNZIP_ATTACHMENT" != "" ]
then
	if [ ! -f user/$ATTACHMENT ]
	then
		echo "$ATTACHMENT not found" >&2
		exit 1
	fi
	unzip -q user/$ATTACHMENT
	rm -f user/$ATTACHMENT
fi

cd user

# Pull a file.
if [ "$PULL" != "" ]
then
	if [ ! -f $PULL ]
	then
		echo "Pull file not found $PULL" >&2
		exit 1
	fi
	mv $PULL ..
fi

# Unzip given file.
if [ "$UNZIP" != "" ]
then
	if [ ! -f $UNZIP ]
	then
		echo "Zip file not found $UNZIP" >&2
		exit 1
	fi
	unzip -q $UNZIP
	rm -f $UNZIP
fi

# Convert charset.
if [ "$CHARSET" != "" ]
then
	find . -type f -exec $ROOT/scripts/_tocharset.sh $CHARSET {} ../tmpiconv \;
fi

# Add contents of a directory.
DIRS=( "$ADD" )
for d in $DIRS
do
	ADD_DIR=$ROOT/exercises/$d
	if [ ! -d $ADD_DIR ]
	then
		echo "Add directory not found $ADD_DIR" >&2
		exit 1
	fi
	find $ADD_DIR -mindepth 1 -maxdepth 1 -exec cp -r {} . \;
done
