#!/bin/bash

# This script tries to set up A+ for testing. 

cd ..

VENV_DIR=../aplusenv
VENV_PYTHON=$VENV_DIR/bin/python
FIXTURE_DIR=course/fixtures


#remove old test environment
if [ -d $VENV_DIR ]; then
    rm -R $VENV_DIR
fi
if [ -f aplus.db ]; then
    rm aplus.db
fi
mkdir -p $FIXTURE_DIR
if [ -f $FIXTURE_DIR/initial_data.json ]; then
    rm $FIXTURE_DIR/initial_data.json
fi


# create the virtualenv
python venv_bootstrap.py $VENV_DIR


# create the database
$VENV_PYTHON manage.py syncdb --noinput
$VENV_PYTHON manage.py migrate


#insert test data
cp doc/initial_data.json $FIXTURE_DIR/initial_data.json
$VENV_PYTHON manage.py migrate course


#create super user
$VENV_PYTHON manage.py createsuperuser


