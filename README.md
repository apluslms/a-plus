A+
==

"We present a design and open source implementation for a service oriented e-learning system, which utilizes external services for supporting a wide range of learning content and also offers a REST API for external clients to fetch information stored in the system."

Karavirta, V. & Ihantola, P. & Koskinen, T. (2013)
Service-Oriented Approach to Improve Interoperability of E-Learning Systems
http://dx.doi.org/10.1109/ICALT.2013.105

The system has since been developed by various contributors at Aalto University, Finland.

Requirements
------------

A+ is a Django 1.7+ and Python 3 application which has been run in production using Postgresql database, Apache 2 and uwsgi. Consider using `virtualenv` and `pip3 install -r requirements.txt`. Create `local_settings.py` in the same directory with `settings.py` and override necessary Django settings. At least `DEBUG`, `SECRET_KEY` and `DATABASES` must be set in case of deployment. The server process needs write access to the `media` directory.

Testing environment
-------------------

See [doc/README.md](doc/README.md) on how to create and run a test environment for development.

Structure
---------

Included Django applications
* `course` : The course instances
* `exercise` : Learning modules and exercises for the course instances
* `userprofile` : Additional user information and groups
* `django_shibboleth` : Handles users for Apache Shibboleth headers
* `notification` : User messaging framework
* `inheritance` : Utilities for model class hierarchy
* `external_services` : Linking to external services, optionally LTI authenticated
* `apps` Provides plugins (tabs disabled) that integrate additional parts to main content
