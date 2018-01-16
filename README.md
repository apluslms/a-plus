<<<<<<< HEAD
A+ ![Build status](http://plustest.cs.hut.fi/buildStatus/icon?job=A-plus-test-MASTER)
=====================================================================================

"We present a design and open source implementation for a service oriented e-learning system, which utilizes external services for supporting a wide range of learning content and also offers a REST API for external clients to fetch information stored in the system."

Karavirta, V. & Ihantola, P. & Koskinen, T. (2013)
Service-Oriented Approach to Improve Interoperability of E-Learning Systems
http://dx.doi.org/10.1109/ICALT.2013.105

The system has since been developed by various contributors at Aalto University, Finland.

Requirements
------------

A+ is a Django 1.7+ and Python 3.4+ application which has been run in production using Postgresql database, Apache 2 and uwsgi.
See [doc/DEPLOYMENT.md](doc/DEPLOYMENT.md) for further deployment instructions.
Consider using `virtualenv` and `pip3 install -r requirements.txt`.
Create `local_settings.py` and override necessary Django settings from `aplus/settings.py`.
At least `DEBUG`, `SECRET_KEY` and `DATABASES` must be set in case of deployment.
The server process needs write access to the `media` directory.

Development
-----------

See [doc/README.md](doc/README.md) on how to create and run a test environment for development.
The [doc/GRADERS.md](doc/GRADERS.md) describes grader service protocols and [doc/example_grader.py](doc/example_grader.py) is a minimal sample for implementing different kind of exercise graders.
A separate grading framework application supporting the A+ protocol exists at https://github.com/Aalto-LeTech/mooc-grader

The [selenium_test/](selenium_test) offers an integration test suite using the Selenium Firefox driver.

Code Organization
-----------------

* [aplus/](aplus) : Django main settings
* [userprofile/](userprofile) : User information and authentication
* [django_shibboleth/](django_shibboleth) : Handles users for Apache Shibboleth request headers
* [course/](course) : The course instances, modules and chapters
* [exercise/](exercise) : Exercises and submissions to them
* [deviations/](deviations) : Student deviations to submission rules
* [notification/](notification) : User messaging framework
* [edit_course/](edit_course) : The course editing for teachers
* [inheritance/](inheritance) : Utilities for model class hierarchy
* [external_services/](external_services) : Linking to external services, optionally LTI authenticated
* [apps/](apps) : Provides plugins that can integrate additional content to course instances
* [api/](api) : An HTTP service API for accessing A+ data
* [redirect_old_urls/](redirect_old_urls) : Redirections from the most important old URL targets
* [lib/](lib) : General library code
* [templates/](templates) : General site templates
* [assets/](assets) : Static web server assets e.g. javascript, styles and images
* [media/](media) : User uploaded files
=======
This grading service accepts anonymous submissions for grading via HTTP. The
grading can be done synchronously or asynchronously using a submission queue.
The results are delivered to the calling system and the grader does not keep
any record other than service logs. The grader is designed to serve exercises
for the A+ learning system. A farm of individual grading servers can be setup
to handle large amount of submissions.

The grader is implemented on Django 1.9 (`grader/settings.py`) and grading
queue on Celery 3.1 (`grader/tasks.py`). The application is tested on both
Python 2.7 and 3.4. Actual grading is typically executed via shell scripts in
a Linux chroot sandbox. On an Ubuntu system the sandbox can be created with
the `manage_sandbox.sh` script.

The grader can be run stand alone without the full stack to test graders in
the local system environment. The grader is designed to be extended for
different courses and exercise types. Course and exercise configuration is in
`courses` directory where further documentation and examples are available.

Installing for development
==========================

> 6/2014 - Ubuntu 12.04.4

1. ### Clone the software

	General requirements

		sudo apt-get install git libjpeg-dev
		sudo apt-get install libxml2-dev libxslt-dev zlib1g-dev

	Install software

		git clone https://github.com/Aalto-LeTech/mooc-grader.git
		mkdir mooc-grader/uploads

2. ### Python requirements (2.7 should work too)

		sudo apt-get install python3 python3-dev python3-pip

	OR install from source.

		sudo apt-get install build-essential libssl-dev libsqlite3-dev
		wget https://www.python.org/ftp/python/3.4.3/Python-3.4.3.tar.xz
		tar xvf Python-3.4.3.tar.xz
		cd Python-3.4.3
		./configure
		make
		sudo make install

	Make sure pip and virtualenv are installed.

		sudo pip3 install virtualenv

	Then, create virtual environment with grader requirements.

		virtualenv -p python3 venv
		source venv/bin/activate
		pip install -r mooc-grader/requirements.txt

3. ### Testing grader application

		cd mooc-grader
		python manage.py runserver

	In addition, the exercise configuration and grading of individual
	exercises can be tested from command line.

		python manage.py exercises
		python manage.py grade

4. ### For configuring courses and exercises, see

	`courses/README.md`

Installing the full stack
=========================

> 6/2014 - Ubuntu 12.04.4

0. ### User account

	On a server, one can install mooc-grader for a specific grader
	user account.

		sudo useradd -mUrd /srv/grader grader
		cd

	Then follow the "Installing for development" and continue from here.

1. ### Web server configuration

	Install uwsgi to run WSGI processes. The **mooc-grader directory
	and user must** be set in the configuration files.

	#### uWSGI with Upstart (Ubuntu < 15.04)

		source venv/bin/activate
		pip install uwsgi
		sudo mkdir -p /etc/uwsgi
		sudo mkdir -p /var/log/uwsgi
		sudo cp doc/etc-uwsgi-grader.ini /etc/uwsgi/grader.ini
		sudo cp doc/etc-init-uwsgi.conf /etc/init/uwsgi.conf
		# EDIT /etc/uwsgi/grader.ini
		# EDIT /etc/init/uwsgi.conf
		sudo touch /var/log/uwsgi/grader.log
		sudo chown -R [shell-username]:users /etc/uwsgi /var/log/uwsgi

	NOTE that the ownership of the log file is required for graceful
	restarts using touch. Operate the workers using:

		sudo status uwsgi
		sudo start uwsgi
		# Graceful application reload
		touch /etc/uwsgi/grader.ini

	#### uWSGI with systemd (Ubuntu >= 15.04)

		source venv/bin/activate
		pip install uwsgi
		sudo mkdir -p /etc/uwsgi
		sudo mkdir -p /var/log/uwsgi
		sudo cp doc/etc-uwsgi-grader.ini /etc/uwsgi/grader.ini
		sudo cp doc/etc-systemd-system-uwsgi.service /etc/systemd/system/uwsgi.service
		# EDIT /etc/uwsgi/grader.ini
		# EDIT /etc/systemd/system/uwsgi.service, set the correct uwsgi path to ExecStart
		sudo touch /var/log/uwsgi/grader.log
		sudo chown -R [shell-username]:users /etc/uwsgi /var/log/uwsgi

	Operate the workers:

		systemctl status uwsgi
		sudo systemctl start uwsgi
		sudo systemctl enable uwsgi  # start on boot
		# Graceful application reload
		touch /etc/uwsgi/grader.ini

	#### nginx

		sudo apt-get install nginx
		# Configure based on doc/etc-nginx-sites-available-grader

	#### apache2

		sudo apt-get install apache2 libapache2-mod-uwsgi
		# Configure based on doc/etc-apache2-sites-available-grader


2. ### Chroot sandbox creation

	Creates a chroot environment to `/var/sandbox/` where tests
	can not escape the enclosing directory. The script can be run
	again to update the sandbox with changes.

		sudo mooc-grader/manage_sandbox.sh create all

	Changing the sandbox location requires changing path in
	`scripts/chroot_execvp.c` and using an argument with the
	management script.

3. ### Asynchronous grading queue

	Install rabbitmq and enable HTTP management interface.

		sudo apt-get install rabbitmq-server
		sudo /usr/lib/rabbitmq/bin/rabbitmq-plugins enable rabbitmq_management

	Create `mooc-grader/settings_local.py` and override necessary configuration, e.g.

	* `CELERY_BROKER`: the queue URL (RabbitMQ service)
	* `CELERY_TASK_LIMIT_SEC`: the timeout for grading a task
	* `QUEUE_ALERT_LENGTH`: the error log threshold
	* `SANDBOX_LIMITS`: the default time/memory limits for sandbox

	The celery queue worker can now be tested in console.
	(Inside the mooc-grader directory with the virtual environment activated.)

		celery -A grader.celery worker

4. ### Run Celery as daemon on boot

	Following copies daemon configuration and script in their place
	and registers the daemon for default run levels and starts it up.
	The **mooc-grader directory and user must** be set in the
	`/etc/default/celeryd`.

		sudo cp doc/etc-default-celeryd /etc/default/celeryd
		# EDIT /etc/default/celeryd
		sudo cp doc/etc-init.d-celeryd /etc/init.d/celeryd
		sudo chmod a+x /etc/init.d/celeryd
		sudo update-rc.d celeryd defaults
		sudo /etc/init.d/celeryd start

5. ### Django application settings for deployment

	When deploying, overwrite necessary configurations in `mooc-grader/settings_local.py`:
	`SECRET_KEY`, `AJAX_KEY`, `DEBUG`, `ALLOWED_HOSTS`

	If `gitmanager` is used to update course content via Git operations, enable it in
	`settings_local.py`:

		ADD_APPS = (
			'gitmanager',
		)

	`gitmanager` uses a database. If `sqlite3` is used (in `settings.py`), it must be installed:

		sudo apt-get install sqlite3 libsqlite3-dev

	Django must install the database schema for the `gitmanager` (Python virtual environment must be activated):

		python manage.py migrate

	The `gitmanager` requires a crontab for the root account:

		sudo crontab -u root doc/gitmanager-root-crontab


6. ### X virtual frame buffer (if required)

	For tests requiring X display server xvfb can be used at DISPLAY=:0.
	Such tests typically run GUI code or WWW browser using Selenium.
	Following installs xvfb and copies the daemon script in place and
	registers the daemon for default run levels and starts it up.

		sudo apt-get install xvfb
		sudo cp doc/etc-init.d-xvfb /etc/init.d/xvfb
		sudo chmod a+x /etc/init.d/xvfb
		sudo update-rc.d xvfb defaults
		sudo /etc/init.d/xvfb start
>>>>>>> 6084eaa985868bc28e2c48fd1d9fa2b2462c7ca0
