#!/bin/bash
#
# Invokes a third party expaca testing application that is not freely available.
#
cd `dirname $0`/..
source scripts/_config.sh

DIR=
TESTNAME=checkingRule.xml
TESTMODEL=model
TESTFILES=CheckingFiles

# Parse arguments.
source scripts/sandbox/_args.sh
while args
do
	case "$ARG_ITER" in
		--dir) DIR=$ARG_NEXT; args_skip ;;
		--rulefile) TESTNAME=$ARG_NEXT; args_skip ;;
		--modeldir) TESTMODEL=$ARG_NEXT; args_skip ;;
		--filesdir) TESTFILES=$ARG_NEXT; args_skip ;;
		*) ;;
	esac
done
args_require_dir --dir $DIR

cd $DIR

# Check and unzip test files.
if [ ! -f user/$ATTACHMENT ]
then
	echo "$ATTACHMENT not found" >&2
	exit 1
fi
unzip -q user/$ATTACHMENT
rm -f user/$ATTACHMENT

# Add checking files to user/ and model/.
if [ -d $TESTFILES ]
then
	find $TESTFILES -mindepth 1 -maxdepth 1 -exec cp -rf {} user/ \; -exec cp -rf {} $TESTMODEL/ \;
fi

# Link expaca configuration.
ln -sf $ROOT/expaca/data/expaca_config.dtd .
ln -sf $ROOT/expaca/data/expaca_config.xml .

/usr/local/bin/expaca user $TESTMODEL $TESTNAME -

exit 0
