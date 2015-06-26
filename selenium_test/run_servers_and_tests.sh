#!/bin/bash

cd `dirname "$0"`/test

TEST=nosetests
XVFB=`which xvfb-run`

if [ -z "$WORKSPACE" ]; then
	WORKSPACE=.
fi

if [ -n "$VENV_HOME" ]; then
	TEST="$VENV_HOME/nosetests --verbosity=3 --with-xunit --xunit-file=$WORKSPACE/selenium_test_report.xml"
fi

trap '../kill_servers.sh' EXIT
../run_servers.sh

if [ -x "$XVFB" ]; then
	$XVFB $TEST *_test.py
else
	$TEST *_test.py
fi
