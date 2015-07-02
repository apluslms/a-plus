Installing Local Test Environment for A+
========================================

## Prerequisites

The script `create_test_environment.sh` is intended for Unix environments. You need to have Python
virtualenv and xml-related packages installed. Follow the OS specific instructions below to install
everything you need. 

### Ubuntu

    sudo apt-get install python-virtualenv libxml2-dev libxslt-dev python-dev libyaml-dev zlib1g-dev
    sudo pip install pyyaml

### Fedora
    
    sudo yum install python-virtualenv libxml2-devel libxslt-devel python-devel

### OS X (Yosemite)

These instructions use the [Homebrew](http://brew.sh/) package manager to install the prerequisites.
Other package managers/tools may also work.

    # install/update Xcode command line tools
    xcode-select --install
    # use brew to install prerequisites
    brew install python libxml2 libxslt
    # use pip to install virtualenv (pip came with brew's python)
    pip install virtualenv


## Creating and running a Local A+ Development Environment

    # run the script
    ./create_test_environment.sh [path_to_virtualenv]

The script will try to do the following things:

  - Install virtualenv with all the dependencies of A+
  - Create a SQLite database with some initial data (from initial_data.json)
  - Finally it will prompt you to create a super user account (that you can use to log in to the local A+)

After running the script (or setting up the environment manually) you can start
the A+ server by running (from the project root folder):

    PATH_TO_VIRTUALENV/bin/python manage.py runserver 8000

Unit tests can be executed by running (from the project root folder):

    PATH_TO_VIRTUALENV/bin/python manage.py test


## Example grader

If you've loaded the initial data the example exercise relies on you can use the external grader server
(example_grader.py) running on port 8888. This grader can be started by running (from this folder):
    
    PATH_TO_VIRTUALENV/bin/python example_grader.py

Now the example exercise in A+ should work and you should get points from submissions accordingly.


## Selenium integration tests

Selenium tests are designed to run against a certain database state and service ports. The tests will open and direct Firefox browser windows.

### Prerequisites

- Firefox browser installed
- Following packages in the virtualenv

	source PATH_TO_VIRTUALENV/bin/activate
	pip install selenium nose

### Running

To setup the servers and run all the tests at one go (with virtualenv activated):

	selenium_test/run_servers_and_tests.sh
