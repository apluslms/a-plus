#!/bin/bash

# This script tries to set up A+ for testing. 

cd ..

python venv_bootstrap.py ../aplusenv              # create the virtualenv

../aplusenv/bin/python manage.py syncdb --noinput # create the sqlite database
../aplusenv/bin/python manage.py migrate course   # first do migrations to the course...
../aplusenv/bin/python manage.py migrate          # ...then for the rest
mkdir course/fixtures
cp doc/initial_data.json course/fixtures/         # copy initial course data...
../aplusenv/bin/python manage.py migrate course   # ...and get it do db

../aplusenv/bin/python manage.py createsuperuser  # finally create a super user


