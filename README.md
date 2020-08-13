A+ ![Build status](http://plustest.cs.hut.fi/buildStatus/icon?job=A-plus-test-MASTER)
=====================================================================================

"We present a design and open source implementation for a service oriented e-learning system, which utilizes external services for supporting a wide range of learning content and also offers a REST API for external clients to fetch information stored in the system."

Karavirta, V. & Ihantola, P. & Koskinen, T. (2013)
Service-Oriented Approach to Improve Interoperability of E-Learning Systems
http://dx.doi.org/10.1109/ICALT.2013.105

The system has since been developed by various contributors at Aalto University, Finland.

Requirements
------------

A+ is a Django 2.2 and Python 3.5+ application which has been run in production using Postgresql database, Apache 2 (or Nginx) and uwsgi.
See [doc/DEPLOYMENT.md](doc/DEPLOYMENT.md) for further deployment instructions.
Consider using `virtualenv` and `pip3 install -r requirements.txt`.
Create `local_settings.py` and override necessary Django settings from `aplus/settings.py`.
At least `DEBUG`, `SECRET_KEY` and `DATABASES` must be set in case of deployment.
The server process needs write access to the `media` directory.

Development
-----------

See [doc/README.md](doc/README.md) on how to create and run a test environment for development.
The [doc/GRADERS.md](doc/GRADERS.md) describes the assessment protocol supported by A+.
Additionally, there is a minimal example grader in [doc/example_grader.py](doc/example_grader.py), which can be used to start a new service.
A list of existing assessment services and other tools can be found in [the project github page](https://apluslms.github.io/components/).

The [selenium_test/](selenium_test) offers an integration test suite using the Selenium Firefox driver.

Code Organization
-----------------

* [aplus/](aplus) : Django main settings
* [userprofile/](userprofile) : User information and authentication
* [shibboleth_login/](shibboleth_login) : User authentication via external Shibboleth login. Requires Shibboleth configuration for the Apache/Nginx web server.
* [course/](course) : The course instances, modules and chapters
* [exercise/](exercise) : Exercises and submissions to them
* [deviations/](deviations) : Student deviations to submission rules (deadline extensions and extra submission attempts)
* [notification/](notification) : User messaging framework
* [edit_course/](edit_course) : The course editing for teachers
* [inheritance/](inheritance) : Utilities for model class hierarchy
* [external_services/](external_services) : Linking to external services, optionally LTI authenticated
* [apps/](apps) : Provides plugins that can integrate additional content to course instances
* [api/](api) : An HTTP REST service API for accessing A+ data
* [redirect_old_urls/](redirect_old_urls) : Redirections from the most important old URL targets
* [lib/](lib) : General library code
* [templates/](templates) : General site templates
* [assets/](assets) : Static web server assets, e.g., JavaScript, styles and images
* [assets_src/](assets_src) : Asset packages (as npm packages), which should populate `assets/` with compiled files.