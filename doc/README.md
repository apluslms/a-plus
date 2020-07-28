Installing Local Test Environment for A+
========================================

## Prerequisites

Containers are heavily used to support local development and to power the CI/CD pipeline.
Thus, you need to have `docker`, `docker-compose` and `drone` commands available.
Also, you need a `docker-compose.yml` with the relevant services.
So, follow the [A+ LMS quick start guide](https://apluslms.github.io/guides/quick/) to get a course, with the compose file, and the Docker stuff.
For the `drone` command, follow the [drone cli installation instructions](https://docs.drone.io/cli/install/).

Some parts are still easier to do without containers, so ensure you have `python3` and Python module `venv` (or `virtualenv`).
For example, install packages `python3` and `python3-venv` in Debian or Ubuntu.
As usual, create a Python virtual environment with `python3 -m venv venv` (e.g. in the project root), activate it with `source venv/bin/activate`, and install modules with `pip3 install -r requirements.txt`.

## Running a Local A+ Development Environment

The repo [run-aplus-front](https://github.com/apluslms/run-aplus-front) implements a Docker image of the A+ portal.
The image contains all the support services and also supports mounting a development code.

To use development code, you need to mount the code in the `docker-compose.yml`.
That is done by adding a line to the `volumes` section.
There are two possible destinations: `/srv/aplus/` and `/src/aplus`.
First will allow the Django process to reload the code without stoping the container, but features which require the write access are not possible, e.g., translations.

```yaml
services:
  # ...
  plus:
    image: apluslms/run-aplus-front
    volumes:
    - data:/data
    # mount development version to /srv/aplus, when write access is not required
    - /home/user/a-plus/:/srv/aplus/:ro
    # or to /src/aplus, when write access is required
    #- /home/user/a-plus/:/src/aplus/:ro
    ports:
      - "8000:8000"
    depends_on:
      - grader
# ...
```

## Running tests

Before creating a pull-request, you should verify the code is still working against existing tests.
Even better, you should write more tests, when possible!
Nevertheless, you can do that on the host with the command `venv/bin/python manage.py test` (this assumes you did the the virtual environment installation from above).

## Selenium integration tests

Selenium tests are designed to run against a certain database state and service ports.
The tests will automatically open and direct Firefox browser windows.
Currently, the tests depend on Unix type shell.
All the following commands assume that the project virtualenv has been activated:

		cd [project_root]
		source PATH_TO_VIRTUALENV/bin/activate

### Prerequisites

  - Firefox browser installed
  - Python modules for testing in the virtualenv (`pip install -r requirements_testing.txt`)

### Running

To setup the servers and run all the tests at one go:

	selenium_test/run_servers_and_tests.sh

Running individual tests:

	cd selenium_test/test/
	../run_servers.sh

	python login_test.py
	python home_page_test.py

	../kill_servers.sh
