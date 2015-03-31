#!/bin/bash

# This script tries to set up A+ for testing. 

cd ..

VENV_DIR=../aplusenv
VENV_PYTHON=$VENV_DIR/bin/python


# (re)create test environment
if [ -d $VENV_DIR ]; then
    rm -R $VENV_DIR
fi
python venv_bootstrap.py $VENV_DIR

# (re)create the database
if [ -f aplus.db ]; then
    while true; do
        read -p "Do you wish to reset the database as well (Y/N)?" yn
        case $yn in
            [Yy]*)
                rm aplus.db
                $VENV_PYTHON manage.py syncdb --noinput
                $VENV_PYTHON manage.py migrate
                $VENV_PYTHON manage.py loaddata doc/initial_data.json
                $VENV_PYTHON manage.py createsuperuser
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



