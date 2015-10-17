This grading service accepts anonymous submissions for grading via HTTP. The
grading can be done synchronously or asynchronously using a submission queue.
The results are delivered to the calling system and the grader does not keep
any record other than service logs. The grader is designed to serve exercises
for the A+ learning system. A farm of individual grading servers can be setup
to handle large amount of submissions.

The grader is implemented on Django 1.7 (`grader/settings.py`) and grading
queue on Celery 3.1 (`grader/tasks.py`). The application is tested on both
Python 2.7 and 3.4. Actual grading is typically executed via shell scripts in
a Linux chroot sandbox. On an Ubuntu system the sandbox can be created with
the `manage_sandbox.sh` script.

The grader can be run stand alone without the full stack to test graders in
the local system environment. The grader is designed to be extended for
different courses and exercise types. Course and exercise configuration is in
`exercises` directory where exercise documentation and examples are available.

Installing for development
==========================

> 6/2014 - Ubuntu 12.04.4

1. ### Clone the software

		git clone https://github.com/Aalto-LeTech/mooc-grader.git
		mkdir mooc-grader/uploads

2. ### Python requirements (2.7 should work too)

		sudo apt-get install python3 python3-dev python3-pip
		sudo apt-get install libxml2-dev libxslt-dev

	OR install from source.

		sudo apt-get install build-essential libssl-dev libsqlite3-dev
		wget https://www.python.org/ftp/python/3.4.3/Python-3.4.3.tar.xz
		tar xvf Python-3.4.3.tar.xz
		cd Python-3.4.3
		./configure
		make
		sudo make install

	Then, create virtual environment with grader requirements.

		sudo pip3 install --upgrade pip
		sudo pip3 install virtualenv

		virtualenv -p python3 venv
		source venv/bin/activate
		pip install -r mooc-grader/requirements.txt

3. ### Testing grader application

		python manage.py runserver

	In addition, the exercise configuration and grading of individual
	exercises can be tested from command line.

		python manage.py exercises
		python manage.py grade

4. ### For configuring courses and exercises, see

	`exercises/README.md`

Installing the full stack
=========================

> 6/2014 - Ubuntu 12.04.4

1. ### Further requirements on top of the development

		sudo apt-get install rabbitmq-server
		sudo /usr/lib/rabbitmq/bin/rabbitmq-plugins enable rabbitmq_management

2. ### Configuration

	Create `settings_local.py` and override necessary configuration.

	* `CELERY_BROKER`: the queue URL (RabbitMQ service)
	* `CELERY_TASK_LIMIT_SEC`: the timeout for grading a task
	* `QUEUE_ALERT_LENGTH`: the error log threshold
	* `SUBMISSION_PATH`: the file submission directory
	* `SANDBOX_LIMITS`: the default time/memory limits for sandbox

	The celery queue worker can now be tested.

		celery -A grader.tasks worker

3. ### Chroot sandbox creation

	Creates a chroot environment to `/var/sandbox/` where tests
	can not escape the enclosing directory. The script can be run
	again to update the sandbox with changes.

		sudo mooc-grader/manage_sandbox.sh create all

	Changing the sandbox location requires changing path in
	`scripts/chroot_execvp.c` and using an argument with the
	management script.

5. ### X virtual frame buffer

	For tests requiring X display server xvfb can be used. These
	tests include in browser tests. Following installs xvfb and copies
	the daemon script. Finally X daemon is started at DISPLAY=:0

		sudo apt-get install xvfb
		sudo cp doc/etc-init.d-xvfb /etc/init.d/xvfb
		sudo chmod a+x /etc/init.d/xvfb
		sudo update-rc.d xvfb defaults
		sudo /etc/init.d/xvfb start

6. ### Celeryd installation

	Following copies daemon configuration and script in their place
	and registers daemon for default run levels and starts it up.
	The **mooc-grader directory and user must** be set in the
	`/etc/default/celeryd`.

		sudo cp doc/etc-default-celeryd /etc/default/celeryd
		sudo cp doc/etc-init.d-celeryd /etc/init.d/celeryd
		sudo chmod a+x /etc/init.d/celeryd
		sudo update-rc.d celeryd defaults
		sudo /etc/init.d/celeryd start

7. ### Web server configuration

	### TODO update to nginx and uwsgi for Python 3.

	__Apache__: Edit your `/etc/apache2/sites-available/sitename`.

		WSGIDaemonProcess grader user=username group=username python-path=/home/username/mooc-grader:/home/username/venv/lib/python2.7/site-packages
		WSGIProcessGroup grader
		WSGIScriptAlias / /home/username/mooc-grader/grader/wsgi.py
		Alias /static/ /home/username/mooc-grader/static/
		Alias /robots.txt /home/username/mooc-grader/static/robots.txt
		<Directory /home/username/mooc-grader/static/>
			Order allow,deny
			allow from all
		</Directory>
