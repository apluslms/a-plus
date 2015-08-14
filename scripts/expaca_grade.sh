#!/bin/bash
#
# Invokes a third party expaca testing application that is not freely available.
#
cd `dirname $0`/..
source scripts/_config.sh

DIR=
TESTDIR=
TESTNAME=checkingRule.xml
TESTMODEL=model
TESTFILES=CheckingFiles

# Parse arguments.
source scripts/sandbox/_args.sh
while args
do
	case "$ARG_ITER" in
		--dir) DIR=$ARG_NEXT; args_skip ;;
		--testdir) TESTDIR=$ARG_NEXT; args_skip ;;
		--rulefile) TESTNAME=$ARG_NEXT; args_skip ;;
		--modeldir) TESTMODEL=$ARG_NEXT; args_skip ;;
		--filesdir) TESTFILES=$ARG_NEXT; args_skip ;;
		*) ;;
	esac
done
args_require_dir --dir $DIR
args_require --testdir $TESTDIR

cd $DIR

# Check test contents.
TEST=$ROOT/exercises/$TESTDIR
if [ ! -d $TEST ]
then
	echo "Test directory \"$TEST\" not found" >&2
	exit 1
fi
if [ ! -d $TEST/$TESTMODEL ]
then
	echo "Test directory does not contain model directory at \"$TESTMODEL\"" >&2
	exit 1
fi
if [ ! -f $TEST/$TESTNAME ]
then
	echo "Test rule XML not found at \"$TEST/$TESTNAME\"" >&2
	exit 1
fi

# Copy model solution and test configuration.
cp -r $TEST/$TESTMODEL ./model
cp $TEST/$TESTNAME checkingRule.xml

# Add checking files to user/ and model/.
if [ -d $TEST/$TESTFILES ]
then
	find $TEST/$TESTFILES -mindepth 1 -maxdepth 1 -exec cp -r "{}" user/ \; -exec cp -r "{}" model/ \;
fi

# Link expaca configuration.
ln -sf $ROOT/expaca/data/expaca_config.dtd .
ln -sf $ROOT/expaca/data/expaca_config.xml .

/usr/local/bin/expaca user model checkingRule.xml -

exit 0
