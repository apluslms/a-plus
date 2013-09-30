Instructions for installing test environment for A+
=============


Test environment script tries to create an environment where A+ can be run for testing. Script will try to do the following things:

  - Install virtualenv with all the dependencies of A+
  - Create a SQLite database with some initial data (from initial_data.json)
  - Finally it will prompt you to create a super user account (you can login to your A+ with your A+ speci

After running the script (or setting up the environment manually) you can start the A+ server by running:

    [path_to_virtualenv]/bin/python manage.py runserver 8080

If you've loaded the initial data the example exercise relies on external grader server (example_grader.py) running on port 8888. This grader (found in this folder) can be started by running:

    python example_grader.py

Now the example exercise in A+ should work and you should get points from submissions accordingly.
