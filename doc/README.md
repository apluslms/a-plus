<<<<<<< HEAD
Installing Local Test Environment for A+
========================================


## Prerequisites

You need to have Python 3.4+ and virtualenv installed.
Follow the OS specific instructions below to install everything you need.

### Ubuntu

The "python3" package of Ubuntu/Debian is still Python 3.2.
Until the packaged version is upgraded it is necessary to compile from source.
Other Linux flavors should follow the same pattern (e.g. replace apt-get with yum).

	sudo apt-get install build-essential libssl-dev libsqlite3-dev
	wget https://www.python.org/ftp/python/3.4.3/Python-3.4.3.tar.xz
	tar xvf Python-3.4.3.tar.xz
	cd Python-3.4.3
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

First install Python 3.4 from [python.org](https://www.python.org/downloads/).
Then manually create Python virtualenv.

	cd [project_root]
	C:\Python34\python -m venv [path_to_virtualenv]
	[path_to_virtualenv]/Scripts/activate.bat
	pip install --upgrade pip
	pip install -r requirements.txt

Last manually create Django sqlite database for testing.

	python manage.py migrate
	python manage.py loaddata doc/initial_data.json
	python manage.py createsuperuser


## Running a Local A+ Development Environment

After running the automatic script or setting up the environment manually
you can start the A+ server by running (from the project root folder):

    PATH_TO_VIRTUALENV/bin/python manage.py runserver 8000

Unit tests can be executed by running:

    PATH_TO_VIRTUALENV/bin/python manage.py test


## Example grader

If you've loaded the initial data the example exercise relies on you can use the external grader server
(example_grader.py) running on port 8888. This grader can be started by running:

    cd [project_root]/doc
    PATH_TO_VIRTUALENV/bin/python example_grader.py

Now the example exercise in A+ should work and you should get points from submissions accordingly.


## Selenium integration tests

Selenium tests are designed to run against a certain database state and service ports.
The tests will automatically open and direct Firefox browser windows. Currently the tests
are depended on unix type shell. All the following commands assume that the project
virtualenv is activated:

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
=======
* For installation, see /README.md
* For exercise configuration, see /exercises/README.md

# Grader Filesystem Walkthrough

* `/doc`: Description of the system and material for system administrators.

* `/grader`: Django project settings, urls and wsgi accessor.

	* `tasks.py`: Celery queues asynchronous grading tasks.

	* `runactions.py`: Runs actions in an asynchronous grading task.

	* `actions.py`: Implementations for different grading action types.

* `/templates`: Base templates for default grader pages.

* `/static`: Statical files for default grader pages.

* `/access`: Django application presenting exercises and accepting submissions.

	* `templates`: Default view and grading task templates.

	* `types`: Implementations for different exercise view types.

	* `management`: Commandline interface for testing configured exercises.

* `/util`: Utility modules for HTTP, shell, filesystem access etc.

* `/exercises`: Course directories holding exercise configuration and material.

	* `sample_course`: Different exercise types sampled.

* `/scripts`: Shell scripts that different grading actions utilize.

	* `chroot_execvp.c`: Moves the target directory inside sandboxed system
		and then runs the given command in it as a sandbox user.
		This program should be compiled and setuid set so that anyone
		can run it as a root. This enables running user code safely
		sandboxed from the normal filesystem. In addition to the chroot
		sandbox the network access for uid 666 should be dropped using
		iptables.

			gcc -o chroot_execvp chroot_execvp.c
			sudo chown root:root chroot_execvp
			sudo chmod 4755 chroot_execvp

	* `sandbox`: Scripts meant for running inside the sandbox from location
		`/usr/local/sandbox`. Scripts having the pattern
		`install-*` will be automatically run in alphabetical order
		during sandbox creation and update.

* `/uploads`: Asynchronous graders store submission data in unique directories here.
	After accepting submission a `user` subdirectory holds the user data.
	Grading actions get this directory as a parameter and can change the
	contents. When grading is finished and feedback sent the submission
	data is removed and submission is completely forgotten.

* `/manage_sandbox.sh`: Automatization of the sandbox creation and setup.
	The script can be run more than once for updating the sandbox setup.

# Experimenting with the sandbox

	sudo chroot /var/sandbox

Chrooting changes the root directory of the linux system. A separate filesystem
installation of a Linux system is found inside this directory and user is trapped
inside it until exiting.
>>>>>>> 6084eaa985868bc28e2c48fd1d9fa2b2462c7ca0
