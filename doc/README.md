Installing Local Test Environment for A+
=============

## Prerequisites

The script `create_test_environment.sh` is intended for Unix environments. You
need to have python virtualenv and xml-related packages installed. Follow the OS
specific instructions below to install everything you need.

### Ubuntu

    sudo apt-get install python-virtualenv libxml2-dev libxslt-dev python-dev


### OS X (Yosemite)

These instructions use the [Homebrew](http://brew.sh/) package manager to
install the prerequisites. Other package managers/tools may also work.

    # install/update Xcode command line tools
    xcode-select --install
    # use brew to install prerequisites
    brew install python libxml2 libxslt
    # use pip to install virtualenv (pip came with brew's python)
    pip install virtualenv


## Creating and running a Local A+ Development Environment

Test environment script tries to create an environment where A+ can be run for
testing. Script will try to do the following things:

  - Install virtualenv with all the dependencies of A+
  - Create a SQLite database with some initial data (from initial_data.json)
  - Finally it will prompt you to create a super user account (that you can use to log in to the local A+)

Instructions for running the script:

    # enter this folder
    cd docs
    # run the script
    ./create_test_environment.sh


After running the script (or setting up the environment manually) you can start
the A+ server by running:

    [path_to_virtualenv]/bin/python manage.py runserver 8000

## Example grader

If you've loaded the initial data the example exercise relies on external grader
server (example_grader.py) running on port 8888. This grader (found in this
folder) can be started by running:

    python example_grader.py

Now the example exercise in A+ should work and you should get points from
submissions accordingly.
