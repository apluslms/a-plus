#!/bin/bash
#
# Prepares submitted files for grading by adding supporting files,
# converting character set and other rearrangements.
#
cd `dirname $0`/..
source scripts/_config.sh
source scripts/_copy_util.sh

DIR=
COURSE=
PULL_ATTACHMENT=
UNZIP_ATTACHMENT=
UNZIP=
CHARSET=
CPE=
CP=
MV=
CPPER=
CPGEN=
USERID=
EXERCISE=
GENERATED_INSTANCE_PATH=

if [ -d exercises ]; then
  CDIR=exercises
else
  CDIR=courses
fi

# Parse arguments.
source scripts/sandbox/_args.sh
while args; do
	case "$ARG_ITER" in
		--dir) DIR=$ARG_NEXT; args_skip ;;
		--course_key) COURSE=$ARG_NEXT; args_skip ;;
		--attachment_pull) PULL_ATTACHMENT=$ARG_NEXT; args_skip ;;
		--attachment_unzip) UNZIP_ATTACHMENT=$ARG_NEXT; args_skip ;;
		--unzip) UNZIP=$ARG_NEXT; args_skip ;;
		--charset) CHARSET=$ARG_NEXT; args_skip ;;
		--cp_exercises) CPE=$ARG_NEXT; args_skip ;;
		--cp) CP=$ARG_NEXT; args_skip ;;
		--mv) MV=$ARG_NEXT; args_skip ;;
		--cp_personal) CPPER=$ARG_NEXT; args_skip ;;
		--cp_generated) CPGEN=$ARG_NEXT; args_skip ;;
		--userid) USERID=$ARG_NEXT; args_skip ;;
		--exercise_key) EXERCISE=$ARG_NEXT; args_skip ;;
		--gen_instance_path) GENERATED_INSTANCE_PATH=$ARG_NEXT; args_skip ;;
		*) ;;
	esac
done
args_require_dir --dir $DIR
args_require --course_key $COURSE

ROOT=`pwd`
cd $DIR

# Check and pull attached exercise.
if [ "$PULL_ATTACHMENT" != "" ]; then
	if [ ! -f user/$ATTACHMENT ]; then
		echo "$ATTACHMENT not found" >%2
		exit 1
	fi
	mv user/$ATTACHMENT $PULL_ATTACHMENT
fi

# Check and unzip attached exercise.
if args_true $UNZIP_ATTACHMENT; then
	if [ ! -f user/$ATTACHMENT ]; then
		echo "$ATTACHMENT not found" >&2
		exit 1
	fi
	unzip -q user/$ATTACHMENT
	rm -f user/$ATTACHMENT
fi

cd user

# Unzip user file.
if [ "$UNZIP" != "" ]; then
	if [ ! -f $UNZIP ]; then
		echo "Zip file not found $UNZIP" >&2
		exit 1
	fi
	unzip -q $UNZIP
	rm -f $UNZIP
fi

# Convert character set of user text files.
if [ "$CHARSET" != "" ]; then
	find . -type f -exec $ROOT/scripts/_tocharset.sh $CHARSET {} ../tmpiconv \;
fi

cd ..

# Prepare to travel path->path lists.

list=($CPE)
copy_paths $ROOT/$CDIR/$COURSE/ $DIR/

list=($CP)
copy_paths $DIR/ $DIR/

list=($MV)
list_pos=0
while next_paths $DIR/ $DIR/; do
	if [ -e $SRC ]; then
		mkdir -p `dirname $TO`
		mv $SRC $TO
	else
		echo "Move source not found $SRC" >&2
		exit 1
	fi
done

# personalized exercises: copy personal files and generated exercise instance files
if [ -n "$EXERCISE" ] && [ -n "$USERID" ] && [ -n "$GENERATED_INSTANCE_PATH" ]; then
	list=($CPPER)
	copy_paths $ROOT/exercises-meta/$COURSE/users/$USERID/$EXERCISE/ $DIR/
	
	list=($CPGEN)
	copy_paths "$GENERATED_INSTANCE_PATH"/ $DIR/
fi
