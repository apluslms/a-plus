#!/bin/bash

# This script tries to set up A+ for testing. 

CURRENT_DIR=`pwd`
cd `dirname "$0"`/..

VENV_DIR=../aplusenv
if [ "$1" != "" ]; then
	VENV_DIR="$CURRENT_DIR/$1"
fi
VENV_PIP=$VENV_DIR/bin/pip
VENV_PYTHON=$VENV_DIR/bin/python

# (re)create test environment
if [ -d $VENV_DIR ]; then
    rm -R $VENV_DIR
fi
virtualenv --python=python3 $VENV_DIR
$VENV_PIP install -r requirements.txt

# (re)create the database
if [ -f aplus.db ]; then
    while true; do
        read -p "Do you wish to reset the database as well (Y/N)?" yn
        case $yn in
            [Yy]*)
                rm aplus.db
                break
                ;;
            [Nn]*)
                exit
                ;;
            *)
                echo "Invalid option! Please answer Y (yes) or N (no)"
                ;;
        esac
    done
fi
$VENV_PYTHON manage.py migrate
$VENV_PYTHON manage.py loaddata doc/initial_data.json
$VENV_PYTHON manage.py createsuperuser
