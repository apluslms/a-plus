Installing Local Test Environment for A+
========================================


## Prerequisites

You need to have Python 3.5+ and virtualenv installed.
Follow the OS specific instructions below to install everything you need.

### Ubuntu

Ubuntu 16.04 LTS (xenial) has Python 3.5 in the default package repositories.
Ubuntu 18.04 LTS (bionic) has Python 3.6, which may be used too.

	sudp apt-get install python3

If you had a reason to compile Python from source, the following commands show
how it is done.

	sudo apt-get install build-essential libssl-dev libsqlite3-dev
	wget https://www.python.org/ftp/python/3.5.7/Python-3.5.7.tar.xz
	tar xvf Python-3.5.7.tar.xz
	cd Python-3.5.7
	./configure
	make
	sudo make install

	sudo pip3 install --upgrade pip
	sudo pip3 install virtualenv

	cd [project_root]
	./doc/create_test_environment.sh [optional_path_to_virtualenv]

### OS X

These instructions use the [Homebrew](http://brew.sh/) package manager.
To compile packages also the Xcode command line tool package is required.

    xcode-select --install
    sudo brew install python3

    sudo pip3 install --upgrade pip
    sudo pip3 install virtualenv

	cd [project_root]
	./doc/create_test_environment.sh [optional_path_to_virtualenv]

### Windows

First install Python 3.5 from [python.org](https://www.python.org/downloads/).
Then manually create Python virtualenv.

	cd [project_root]
	C:\Python35\python -m venv [path_to_virtualenv]
	[path_to_virtualenv]/Scripts/activate.bat
	pip install --upgrade pip
	pip install -r requirements.txt

Last manually create Django sqlite database for testing.

	python manage.py migrate
	python manage.py loaddata doc/initial_data.json
	python manage.py createsuperuser


## Running a Local A+ Development Environment

After running the automatic script or setting up the environment manually,
you can start the A+ server by running (from the project root folder):

    PATH_TO_VIRTUALENV/bin/python manage.py runserver 8000

Unit tests can be executed by running:

    PATH_TO_VIRTUALENV/bin/python manage.py test


## Example grader

If you've loaded the initial data the example exercise relies on, you can use the external grader server
(example_grader.py) running on port 8888. This grader can be started by running:

    cd [project_root]/doc
    PATH_TO_VIRTUALENV/bin/python example_grader.py

Now the example exercise in A+ should work and you should get points from submissions accordingly.


## Selenium integration tests

Selenium tests are designed to run against a certain database state and service ports.
The tests will automatically open and direct Firefox browser windows. Currently, the tests
depend on Unix type shell. All the following commands assume that the project
virtualenv has been activated:

		cd [project_root]
		source PATH_TO_VIRTUALENV/bin/activate

### Prerequisites

  - Firefox browser installed
  - Following packages in the virtualenv

		pip install selenium
		pip install nose

### Running

To setup the servers and run all the tests at one go:

	selenium_test/run_servers_and_tests.sh

Running individual tests:

	cd selenium_test/test/
	../run_servers.sh

	python login_test.py
	python home_page_test.py

	../kill_servers.sh
