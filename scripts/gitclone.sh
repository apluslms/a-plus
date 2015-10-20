#!/bin/bash
#
# Clones a user repository and picks out selected files.
#
cd `dirname $0`/..
source scripts/_config.sh

DIR=
RDIR=user-repo
READ=gitsource
FILES=()

# Parse arguments.
source scripts/sandbox/_args.sh
while args
do
	case "$ARG_ITER" in
		--dir) DIR=$ARG_NEXT; args_skip ;;
		--repo_dir) RDIR=$ARG_NEXT; args_skip ;;
		--read) READ=$ARG_NEXT; args_skip ;;
		--files) FILES=( "$ARG_NEXT" ); args_skip ;;
		*) ;;
	esac
done
args_require_dir --dir $DIR
args_require --read $READ

cd $DIR

# Pull the URL file.
if [ ! -f user/$READ ]
then
	echo "Git URL file not found $READ" >&2
	exit 1
fi
SOURCE=`cat user/$READ`
mv user/$READ ..

# Clone the repository.
mkdir $RDIR
cd $RDIR
git clone $SOURCE .
res=$?
if [ $res -eq 0 ]
then
	echo "Finished successfully - HEAD:"
	git rev-parse HEAD
else
	echo "Failed to clone \"$SOURCE\"."
	exit $res
fi
cd ..

# Pick the files.
FSTAT=0
if [ ${#FILES[@]} -gt 0 ]; then
	echo "***APPENDIX***"
	for f in $FILES
	do
		if [ ! -f $RDIR/$f ]
		then
			echo "Failed to find \"$f\"." 1>&2
			FSTAT=1
		else
			TARGET=user/${f##*/}
			mv $RDIR/$f $TARGET
			echo "<p class=\"submission-file\">$f</p><pre>"
			cat $TARGET | sed 's/</\&lt;/g; s/>/\&gt;/g'
			echo "</pre>"
		fi
	done
fi
exit $FSTAT
