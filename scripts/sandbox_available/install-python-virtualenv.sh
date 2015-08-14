#!/bin/bash
#
# An example of setting up a Python 3 virtual environment.
# Minimally this script can be copied as is and related
# pyvirtualenv-requirements.txt edited for the course.
#
VDIR=/usr/local/pyvirtualenvs
VNAME=default
RNAME=pyvirtualenv-requirements.txt

# Check directory to store virtual environments.
mkdir -p $VDIR
cd $VDIR

# Create virtual environment.
if [ ! -d $VNAME ]
then
	virtualenv -p python3.4 $VNAME
fi
source $VNAME/bin/activate
pip install -r $RNAME
deactivate
