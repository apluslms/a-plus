Installing Local Development and Test Environment for A+
========================================================

## Prerequisites

A+ uses containers to support local development and to power the CI/CD pipeline.
Therefore you need to have the following installed:
- [Docker Engine](https://docs.docker.com/engine/install/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- [Drone](https://docs.drone.io/cli/install/)

Note that you will need to have admin rights to install these correctly.

Alternatively, you can have comparable software which enable you to use the commands `docker`, `docker-compose` and `drone`.

If you are going to use Django translations, you must install the GNU **gettext** utilities
- [gettext Ubuntu](https://packages.ubuntu.com/search?keywords=gettext). 
- [gettext Windows](https://mlocati.github.io/articles/gettext-iconv-windows.html)

## Running A+ in a container

1. Follow the installation steps of [course-templates](https://github.com/apluslms/course-templates#installation) to get a template course running.

2. After the installation, you should have A+ running at http://localhost:8000.

3. There are four main user-roles in A+.
These all have readymade accounts, which can be used during development:

   ```
   username: root, password: root (Using A+ as a superuser)
   username: teacher, password: teacher (Using A+ as a teacher)
   username: student, password: student (Using A+ as a student)
   username: assistant, password: assistant (Using A+ as a course assistant)
   ```

4. You can manage the database, user accounts and the content of the presented template course at http://localhost:8000/admin.
You can log in with the superuser-account:

   ```
   username: root, password: root
   ```

5. You can stop the containers with `CTRL + C`.

## Developing the code of A+ (this repository) ###

In order to develop the code within A+, you will need to have this repository, and the aforementioned [course-templates](https://github.com/apluslms/course-templates#installation) forked and/or cloned on your machine.
They can be located in separate directories.

1. Fork this repository by clicking "Fork"-button at the top of the page.

2. Clone the forked repository to your machine with e.g.:

   ```sh
   $ git clone git@github.com:your-github-username/a-plus.git a-plus
   ```

3. To see the changes you make into the code, you need to mount the A+ code in the `docker-compose.yml` file.
The file can be found at the root of the `course-templates` project.
Mounting happens by adding the path to your cloned a-plus directory to the `volumes`-section of the `docker-compose.yml`:

   ```yaml
   # ...
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
If you wish to use features which require write access, e.g. update translations, change the `/srv/` to `/src/`.
Using `/srv/` will allow the Django process to reload the code without stopping the container, but features which require the write access are not possible.

4. Download and build all required support files by running the Drone pipeline, i.e., execute the following in the a-plus project root:

   ```sh
   $ cd [A-PLUS PROJECT ROOT]
   $ drone exec
   ```

5. Run the code within the container:

   ```sh
   $ cd [COURSE-TEMPLATES PROJECT ROOT]
   $ ./docker-up.sh
   ```

**Note that if you wish to develop the code in other services related to A+ (e.g. [mooc-grader](https://github.com/apluslms/mooc-grader), which handles grading of some exercises), you need to follow the instructions given for those services, for example:**

- [Instructions for running the mooc-grader code](https://github.com/apluslms/run-mooc-grader)
- [Instructions for ACOS server](https://github.com/apluslms/run-acos-server)

## Making changes to Sass or JavaScript files

1. Ensure you followed the steps above and have the a-plus code mounted within the `docker-compose.yml` file and the containers running with `./docker-up.sh`.
2. In order to see changes in styles when working on the SCSS files, open up another terminal and run the following commands in the a-plus project root:

    ```sh
   $ cd [A-PLUS PROJECT ROOT]
   $ drone exec
   ```

   After the `drone exec` command finishes its execution, you can start monitoring the changes of the sass compiler by executing the following command.

   ```sh
   $ cd [A-PLUS PROJECT ROOT]
   $ ./dev_assets_watch_sass.sh
   ```

The command will start a container, which will monitor Sass directories for changes and compile them to CSS files when changes are detected.
Note that if you have mounted the code to `/src/`, you need to restart the servers for these updates to take effect.

3. After completing the changes and before committing them, run:

   ```sh
   $ drone exec
   ```

4. Include the built production versions of JavaScript and CSS files (e.g. `css/main.css` and `css/main.css.map`) into the git commit with your changes.

## Making changes to the asset packages

The `assets_src/` contains folders, which are npm packages and should install compiled files to `assets/` as part of `npm install`.
To manage these, you can use `./dev_assets_run_npm.sh`, which runs npm commands in a container.
For example, to update `package.json` of the `translate-js`, run `./dev_assets_run_npm.sh translate-js update`.

## Running tests and updating translations

Some parts are still easier to do without containers, tests and translations are such.
Therefore they are run and updated outside the containers, within a virtual environment.

### Prerequisities

- For Selenium tests:
  * Firefox browser installed
  * xvfb virtual framebuffer installed (`sudo apt-get install xvfb` or `aptdcon --install xvfb`)
- python3 installed
- [Python module venv (or virtualenv)](https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/#installing-virtualenv) installed
- For translations: gettext (`aptdcon --install gettext` or `sudo apt-get install gettext`)

1. Create a virtual environment for a-plus and activate it:

   ```sh
   $ python3 -m venv venv_aplus
   $ source venv_aplus/bin/activate
   ```

2. Install necessary requirements for development:

   ```sh
   $ cd [A-PLUS PROJECT ROOT]
   $ pip3 install --upgrade pip setuptools wheel
   $ pip3 install -r requirements.txt
   ```

3. Create a `local_settings.py` -file at `a-plus/local_settings.py`.
There is an example file `local_settings.example.py`, which you can use as a starting point.

4. Ensure your `local_settings.py` contains at least the following lines:

   ```
   DEBUG = True
   BASE_URL = 'http://localhost:8000/'
   ```

5. Run the existing django migrations:

   ```sh
   $ python3 manage.py migrate
   ```

6. You can now run the local version without a container:

   ```sh
   $ python3 manage.py runserver
   ```

If you need to be able to login or use the admin-page while running the code without a container, you can create a superuser by following [these instructions](https://docs.djangoproject.com/en/3.0/intro/tutorial02/#introducing-the-django-admin).

### Unit tests

1. Run the unit tests:

   ```sh
   $ python3 manage.py test
   ```

### Selenium integration tests

Selenium tests check end-to-end -functioning from a user-perspective.
The tests will automatically open and direct Firefox browser windows.
Currently, the tests depend on a Unix type shell and are run within a virtual environment created above.

1. Install the necessary requirements:

   ```sh
   $ pip3 install -r requirements_testing.txt
   ```

2. Download the latest release of geckodriver (choose the appropriate tar.gz file based on your machine) from https://github.com/mozilla/geckodriver/releases and extract it.

3. Check the path to your extracted geckodriver and add it to PATH:

   ```sh
   $ export PATH=$PATH:/path-to-your-extracted-geckodriver/
   ```

4. To setup the servers and run all the tests at one go:

   ```sh
   $ selenium_test/run_servers_and_tests.sh
   ```

5. Alternatively you can run individual tests:

   ```sh
   $ cd selenium_test/test/
   $ ../run_servers.sh

   $ python3 login_test.py
   $ python3 home_page_test.py

   $ ../kill_servers.sh
   ```

### Updating translations for Finnish and English versions

Before creating a pull request, you need to ensure that the [English strings](https://github.com/apluslms/a-plus/blob/master/locale/en/LC_MESSAGES/django.po) and [Finnish translations](https://github.com/apluslms/a-plus/blob/master/locale/fi/LC_MESSAGES/django.po) are up-to-date.
Translations are handled with [Django](https://docs.djangoproject.com/en/2.2/ref/django-admin/#django-admin-makemessages) and are done outside the container.
If you have added new strings with new string keys, make sure that the keys are in [the correct format](https://apluslms.github.io/contribute/styleguides/gettext/index.md#msgid-format).

1. In order to update the files containing translations, run:

   ```sh
   $ python3 manage.py makemessages --no-obsolete --add-location file --all
   ```

2. You can easily check the lines that were affected:

   ```sh
   $ git diff locale/fi/LC_MESSAGES/django.po
   $ git diff locale/en/LC_MESSAGES/django.po
   ```

3. Add new English texts and Finnish translations for the lines you have created.
   If you wish to edit existing strings, alter the corresponding `msgstr` strings in the English and/or Finnish files.

4. And compile the translations to ensure they are working:

   ```sh
   $ python3 manage.py compilemessages
   ```

The final step can also be used to ensure that the translations work, when the code is run in a container and mounted to `/srv/`.
