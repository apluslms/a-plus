#!/bin/bash

PYTHON=python
DIR=selenium_test

cd `dirname "$0"`/..

if [ "$VENV_HOME" != "" ]; then
	PYTHON=$VENV_HOME/python
fi

export APLUS_DEBUG=True
export APLUS_DB_FILE=$DIR/aplus.db
export APLUS_BASE_URL='http://localhost:8001'
export APLUS_DATABASES="{\"default\": {\"ENGINE\": \"django.db.backends.sqlite3\", \"NAME\": \"$APLUS_DB_FILE\"}}"
export APLUS_CACHES='{"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}'
export APLUS_SECRET_KEY="secret-key"

rm -f $APLUS_DB_FILE

$PYTHON manage.py migrate
$PYTHON manage.py loaddata selenium_test/test_data.json
$PYTHON manage.py shell < selenium_test/add_users.py

cp $APLUS_DB_FILE ${APLUS_DB_FILE}_copy

$PYTHON manage.py runserver 8001 --noreload > $DIR/aplus.out 2>&1 &

unset APLUS_DEBUG APLUS_DB_FILE APLUS_DATABASES APLUS_CACHES APLUS_SECRET_KEY

cd $DIR/grader
rm -f 'db.sqlite3'
$PYTHON manage.py migrate
$PYTHON manage.py runserver 8889 --noreload > ../example_grader.out 2>&1 &

jobs -p > ../server.ports

echo "A+ running at port 8001 and example grader at port 8889."
echo "Ready for Selenium browser tests. Use kill_servers.sh when finished."
