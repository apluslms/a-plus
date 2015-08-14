#!/bin/bash
cd `dirname $0`/..
ROOT=`pwd`
FLAG=/tmp/mooc-grader/gitpull.flag
LOG=$ROOT/gitpull.log

if [ -f $FLAG ]
then
	date > $LOG
	keys=`cat $FLAG`
	rm -f $FLAG
	for key in $keys
	do
		echo "Work on request $key:" >> $LOG
		diri=$ROOT/exercises/$key
		if [ -f $diri/.git ]
		then
			cd $diri
			git pull &>> $LOG
		fi
	done
fi
