#!/bin/bash

PYTHON=python
DIR=selenium_test

cd `dirname "$0"`/..

if [ "$VENV_HOME" != "" ]; then
	PYTHON=$VENV_HOME/python
fi

export APLUS_DB_FILE=$DIR/aplus.db

rm -f $APLUS_DB_FILE

$PYTHON manage.py migrate
$PYTHON manage.py loaddata doc/selenium_test_data.json

cp $APLUS_DB_FILE ${APLUS_DB_FILE}_copy

$PYTHON manage.py runserver 8001 --noreload > $DIR/aplus.out 2>&1 &

unset APLUS_DB_FILE

cd doc
$PYTHON example_grader.py 8889 > ../$DIR/example_grader.out 2>&1 &

jobs -p > ../$DIR/server.ports

echo "A+ running at port 8001 and example grader at port 8889."
echo "Ready for Selenium browser tests. Use kill_servers.sh when finished."
