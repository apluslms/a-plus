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
