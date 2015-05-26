#!/bin/bash

cd `dirname "$0"`/test

TEST=nosetests

if [ "$WORKSPACE" == "" ]; then
	WORKSPACE=.
fi

if [ "$VENV_HOME" != "" ]; then
	TEST=xvfb-run $VENV_HOME/nosetests --verbosity=3 --with-xunit --xunit-file=$WORKSPACE/selenium_test_report.xml
fi

trap '../kill_servers.sh' EXIT
../run_servers.sh
$TEST *_test.py
