#!/bin/bash

cd `dirname "$0"`/test

TEST="python3 -m unittest"
XVFB=`which xvfb-run`

if [ -z "$WORKSPACE" ]; then
	WORKSPACE=.
fi

echo "Starting servers..."

trap '../kill_servers.sh' EXIT
../run_servers.sh

echo "Running tests..."

if [ -x "$XVFB" ]; then
	$XVFB $TEST discover -p "*_test.py"
else
	$TEST discover -p "*_test.py"
fi
