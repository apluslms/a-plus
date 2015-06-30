Automatic browser tests
=======================

This is an integration test suite running with Selenium Firefox
driver against the A+ service and `../doc/example_grader.py`.

### Requirements

	sudo apt-get install firefox xvfb
	[path_to_virtualenv]/bin/pip install selenium nose	

### Usage

First activate the A+ virtualenv.

	source [path_to_virtualenv]/bin/activate

The `run_servers_and_tests.sh` will run all tests in the suite
and take care of setting up and killing the server instances.
If `xvfb` is available Firefox will run headless in a virtual
desktop.

The `run_servers.sh` and `kill_servers.sh` may be used to handle
the Selenium test server instances. Single test cases of form
`test/*_test.py` may be run directly and Selenium will open
Firefox browser to run the tests.
