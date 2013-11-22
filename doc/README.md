Installing Local Test Environment for A+
=============

## Prerequisites

This script is intended for Linux environments (and might work on OS X as well). You need to have python virtualenv and xml-related packages installed. Following command on Ubuntu should install everything you need:

    sudo apt-get install python-virtualenv libxml2-dev libxslt-dev
    
## Creating and running a Local A+ Development Environment

Test environment script tries to create an environment where A+ can be run for testing. Script will try to do the following things:

  - Install virtualenv with all the dependencies of A+
  - Create a SQLite database with some initial data (from initial_data.json)
  - Finally it will prompt you to create a super user account (that you can use to log in to the local A+)

After running the script (or setting up the environment manually) you can start the A+ server by running:

    [path_to_virtualenv]/bin/python manage.py runserver 8080

## Example grader

If you've loaded the initial data the example exercise relies on external grader server (example_grader.py) running on port 8888. This grader (found in this folder) can be started by running:

    python example_grader.py

Now the example exercise in A+ should work and you should get points from submissions accordingly.
