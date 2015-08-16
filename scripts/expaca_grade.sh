#!/bin/bash
#
# Invokes a third party expaca testing application. The expaca application
# is not open source or freely available. It has to be separately acquired
# and installed to the system.
#
cd `dirname $0`/..
source scripts/_config.sh

DIR=
RULE=checkingRule.xml
MODEL=model
USER=user

# Parse arguments.
source scripts/sandbox/_args.sh
while args
do
	case "$ARG_ITER" in
		--dir) DIR=$ARG_NEXT; args_skip ;;
		--rule_file) RULE=$ARG_NEXT; args_skip ;;
		--model_dir) MODEL=$ARG_NEXT; args_skip ;;
		--user_dir) USER=$ARG_NEXT; args_skip ;;
		*) ;;
	esac
done
args_require_dir --dir $DIR

ROOT=`pwd`
cd $DIR

# Link expaca configuration.
ln -sf $ROOT/expaca/data/expaca_config.dtd .
ln -sf $ROOT/expaca/data/expaca_config.xml .

/usr/local/bin/expaca $USER $MODEL $RULE -
exit $?
