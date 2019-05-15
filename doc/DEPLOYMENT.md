A+ Deployment Instructions
==========================

These instructions are checked against Ubuntu, but they should work for Debian and probably for many derivatives of it.

    $ lsb_release -a
    Distributor ID: Ubuntu
    Description:    Ubuntu 18.04.1 LTS
    Release:        18.04
    Codename:       bionic

A+ can be deployed with Apache 2 or NGINX.
Bot web servers work well enough and can support Shibboleth authentication too.
Sadly, combination of NGINX, uWSGI protocol, uWSGI and Shibboleth is not yet tested, but the HTTP proxy version works.

Aalto University is currently running following combinations:

* Apache, uWSGI protocol, uWSGI, Shibboleth, uWSGI logs written to a file
* NGINX, HTTP proxy, gunicorn, Shibboleth, Gunicorn logs written to journald
* NGINX, uWSGI protocol, uWSGI, uWSGI logs written to journald


Table of contents
-----------------

* [Common system configuration](#common-system-configuration)
* [The Application](#the-application)
* [Common Shibboleth configuration](#common-shibboleth-configuration)
* [Apache 2 configuration](#apache-2-configuration)
  * [Shibboleth with Apache 2](#shibboleth-with-apache-2)
* [NGINX configuration](#nginx-configuration)
  * [Shibboleth with NGINX](#shibboleth-with-nginx)
* [Final steps](#final-steps)


Common system configuration
---------------------------

 1. Install required packages

        sudo apt-get install \
          git gettext \
          postgresql memcached \
          uwsgi-core uwsgi-plugin-python3 \
          python3-virtualenv \
          python3-psycopg2 python3-certifi python3-reportlab python3-reportlab-accel

 1. Create a new user for a-plus

        sudo adduser --system --group \
          --shell /bin/bash --home /srv/aplus \
          --gecos "A-plus LMS webapp server" \
          aplus

 1. Create a database and add permissions

        sudo -Hu postgres createuser aplus
        sudo -Hu postgres createdb -O aplus aplus

 1. Create a run directory

        echo "d /run/aplus 0750 aplus www-data - -" \
          | sudo tee /etc/tmpfiles.d/aplus.conf > /dev/null
        sudo systemd-tmpfiles --create


The Application
---------------

 1. Change to our service user

        sudo -u aplus -Hi

 1. Clone the Django application

        # as user aplus in /srv/aplus
        git clone --branch production https://github.com/Aalto-LeTech/a-plus.git
        mkdir a-plus/static \
              a-plus/media

 1. Install virtualenv

        # as user aplus in /srv/aplus
        python3 -m virtualenv -p python3 --system-site-packages venv
        . venv/bin/activate
        pip install -r a-plus/requirements.txt
        pip install -r a-plus/requirements_prod.txt

 1. Configure Django

        # as user aplus in /srv/aplus
        cat > a-plus/aplus/local_settings.py <<EOF
        BASE_URL = "https://$(hostname)/"
        SERVER_EMAIL = "aplus@$(hostname)"
        EOF

        awk '/(BASE_URL|DEBUG|SECRET_KEY|SERVER_EMAIL)/ {next};
             /^## (Database|Cache|Logging)/ {while (/^#/ && getline>0); next} 1' \
          a-plus/aplus/local_settings.example.py >> a-plus/aplus/local_settings.py

        cat >> a-plus/aplus/local_settings.py <<EOF
        ## Database
        DATABASES = {
          'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'aplus',
          }
        }
        ## Cache
        CACHES = {
          'default': {
            'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
            'LOCATION': '127.0.0.1:11211',
          }
        }
        EOF

 1. Run Django deployment tasks

        # as user aplus in /srv/aplus
        . venv/bin/activate
        pushd a-plus

        # migrate db
        ./manage.py migrate

        # compile localisation files
        ./manage.py compilemessages

        # collect static files to be served via dedicated web server
        ./manage.py collectstatic --no-input

        popd

 1. Create uWSGI configuration

        # as user aplus in /srv/aplus
        cat > uwsgi-aplus-web.ini <<EOF
        [uwsgi]
        home=/srv/aplus/venv
        module=aplus.wsgi:application
        enable-threads=True
        processes=4
        threads=2
        max-requests=10000
        harakiri=40
        env=LANG=en_US.UTF-8
        EOF

        cat > uwsgi-aplus-api.ini <<EOF
        [uwsgi]
        home=/srv/aplus/venv
        module=aplus.wsgi:application
        enable-threads=False
        processes=2
        threads=1
        max-requests=10000
        harakiri=40
        env=LANG=en_US.UTF-8
        EOF

    **NOTE**: Select number of processes and threads based on number of of CPUs.
    Probably a good number is around two times cpus for the web (as there is a lot of io wait) and number of cpus for the API.

    You can gracefully chain reload uWSGI services by touching (editing) above files.
    In addition, `sudo systemctl restart aplus-*-uwsgi.service` will also do a chain reload.
    To fully reload python engine, do `stop` and then `start` for these services.

 1. End

    Exit the aplus user shell and return to the admin

        exit


Common Shibboleth configuration
-------------------------------

To configure Shibboleth, follow a guide for your federation.
Because A+ is used a lot in Finnish Universities, we have some examples using [HAKA](https://wiki.eduuni.fi/display/CSCHAKA/Federation), the identity federation for Finnish universities.

For HAKA, you need at least schemas from [here](https://wiki.eduuni.fi/display/CSCHAKA/FunetEduPerson+schema) and metadata certificate from [here](https://wiki.eduuni.fi/display/CSCHAKA/Haka+metadata).
In addition, you can start from [apache2/shibboleth2.xml](apache2/shibboleth2.xml) or [nginx/shibboleth2.xml](nginx/shibboleth2.xml).
More details below for both web servers.


Apache 2 configuration
----------------------

Resources for Apache 2 configuration can be found under [apache2](apache2/) directory.
Following instructions expect that the applocation is installed under `/srv/aplus/a-plus/`.

 1. Install packages

        sudo apt-get install apache2 libapache2-mod-uwsgi
        sudo a2enmod uwsgi
        sudo a2enmod ssl

 1. Configure Apache 2

        sudo ln -s ../sites-available/$(hostname).conf /etc/apache2/sites-enabled/000-$(hostname).conf
        sed -e "s/__HOSTNAME__/$(hostname)/g" /srv/aplus/a-plus/doc/apache2/aplus-apache2.conf \
         | sudo tee /etc/apache2/sites-available/$(hostname).conf > /dev/null

 1. Create systemd service files for uWSGI processes

        sudo cp /srv/aplus/a-plus/doc/apache2/aplus-*-uwsgi.service \
                /etc/systemd/system
        sudo systemctl daemon-reload
        sudo systemctl enable aplus-web-uwsgi.service aplus-api-uwsgi.service
        sudo systemctl start aplus-web-uwsgi.service aplus-api-uwsgi.service

 1. Reload Apache 2

        sudo systemctl restart apahce2.service


### Shibboleth with Apache 2

If you are using shibboleth

 1. Install Shibboleth 2

        sudo apt-get install libapache2-mod-shib2
        sudo a2enmod shib2

 1. Configure Shibboleth for your federation or organization

    Configuration is under directory `/etc/shibboleth`.
    For [HAKA](https://wiki.eduuni.fi/display/CSCHAKA/Federation), there is [apache2/shibboleth2.xml](apache2/shibboleth2.xml).

 1. Shibboleth configuration in The `local_settings.py`

    Map your federations variables to ones used in A+.
    Here is the default mapping, which you can override in `local_settings.py`:

        SHIB_USER_ID_KEY = 'SHIB_eppn'
        SHIB_FIRST_NAME_KEY = 'SHIB_givenName'
        SHIB_LAST_NAME_KEY = 'SHIB_sn'
        SHIB_MAIL_KEY = 'SHIB_mail'
        SHIB_STUDENT_ID_KEY = 'SHIB_schacPersonalUniqueCode'


 1. Reload shibboleth

        sudo systemctl restart shibd.service


NGINX configuration
-------------------

Resources for NGINX configuration can be found under [nginx](nginx/) directory.
Following instructions expect that the applocation is installed under `/srv/aplus/a-plus/`.

 1. Install packges

        sudo apt-get install nginx

 1. Configure NGINX

        if [ -d /etc/nginx/sites-available ] && grep -qs sites-enabled /etc/nginx/nginx.conf; then
            dest=/etc/nginx/sites-available/$(hostname).conf
            sudo ln -s ../sites-available/$(hostname).conf /etc/nginx/sites-enabled/$(hostname).conf
        else
            dest=/etc/nginx/conf.d/$(hostname).conf
        fi
        sed -e "s/__HOSTNAME__/$(hostname)/g" /srv/aplus/a-plus/doc/nginx/aplus-nginx.conf \
         | sudo tee "$dest" > /dev/null

    **NOTE:** If you are going to use shibboleth, then use file [nginx/aplus-nginx-shib.conf](nginx/aplus-nginx-shib.conf).

 1. Create systemd service files for uWSGI processes

        sudo cp /srv/aplus/a-plus/doc/nginx/aplus-*-uwsgi.service \
                /etc/systemd/system
        sudo systemctl daemon-reload
        sudo systemctl enable aplus-web-uwsgi.service aplus-api-uwsgi.service
        sudo systemctl start aplus-web-uwsgi.service aplus-api-uwsgi.service

    If you prefer to use [Gunicorn](https://gunicorn.org/), then you can use [nginx/aplus-gunicorn.service](nginx/aplus-gunicorn.service).

 1. Reload NGINX

        sudo systemctl restart nginx.service


### Shibboleth with NGINX

This guide bases on NGINX module [nginx-http-shibboleth](https://github.com/nginx-shib/nginx-http-shibboleth).
This module uses fastcgi and shibboleth scripts to provide similar integration as Apache 2 plugin.

 1. With Ubuntu xenial or before NGINX 1.11

    With Ubuntu xenial (16.04) and before NGINX 1.11, dynamic modules are not supported, so you need to rebuild the whole NGINX package.

        sudo -i
        cd /usr/src

        apt-get install build-essential devscripts
        apt-get source nginx
        apt-get build-dep nginx

        git clone https://github.com/nginx-shib/nginx-http-shibboleth.git

        pushd nginx-1.*/
        cp debian/rules debian/rules.orig
        cat debian/rules.orig \
          | awk '/add-module=\$\(MODULESDIR\)\/nginx-auth-pam/ {print "--add-module=$(MODULESDIR)/headers-more-nginx-module \\"}1' \
          | awk '/add-module=\$\(MODULESDIR\)\/nginx-auth-pam/ {print "--add-module=/usr/src/nginx-http-shibboleth/ \\"}1' \
          > debian/rules
        rm debian/rules.orig

        dch -lshib "Add Shibboleth"
        dch -r ""

        dpkg-buildpackage -uc -us
        popd

        dpkg -i nginx-full_*shib*_amd64.deb
        exit

 1. Starting from Ubuntu Bionic or NGINX 1.11 we can dynamic modules

    **Write down instructions for this.**

 1. Get NGINX supporting files

        cd /etc/nginx
        wget https://raw.githubusercontent.com/nginx-shib/nginx-http-shibboleth/master/includes/shib_clear_headers

 1. Install required packages

        sudo apt-get install \
          shibboleth-sp2-common \
          shibboleth-sp2-utils \
          shibboleth-sp2-schemas \
          xmltooling-schemas

 1. Create systemd services and sockets for shibboleth scripts

        sudp cp /srv/aplus/a-plus/doc/nginx/shib*.socket \
                /srv/aplus/a-plus/doc/nginx/shib*.service \
                /etc/systemd/system
        sudo systemctl daemon-reload
        sudo systemctl enable shibauthorizer.socket shibresponder.socket
        sudo systemctl start shibauthorizer.socket shibresponder.socket

 1. Configure Shibboleth for your federation or organization

    Configuration is under directory `/etc/shibboleth`.
    For [HAKA](https://wiki.eduuni.fi/display/CSCHAKA/Federation), there is [nginx/shibboleth2.xml](nginx/shibboleth2.xml).

 1. Shibboleth configuration in The `local_settings.py`

    Shibboleth under NGINX delivers shibboleth variables via the request environment,
    thus following mapping is required.
    If your federation uses different variables, remember to change them.

        sudo tee -a /srv/aplus/a-plus/aplus/local_settings.py << EOF
        # Shibboleth
        SHIB_USER_ID_KEY = 'HTTP_SHIB_EPPN'
        SHIB_FIRST_NAME_KEY = 'HTTP_SHIB_GIVENNAME'
        SHIB_LAST_NAME_KEY = 'HTTP_SHIB_SN'
        SHIB_MAIL_KEY = 'HTTP_SHIB_MAIL'
        SHIB_STUDENT_ID_KEY = 'HTTP_SHIB_SCHACPERSONALUNIQUECODE'
        EOF

 1. Reload shibboleth

        sudo systemctl restart shibd.service


Final steps
-----------

 1. Create or set a superuser.

    It is not typically needed to create local superuser, thus you can skip the first part.

        sudo -Hu aplus sh -c "cd /srv/aplus/a-plus;
          ../venv/bin/python3 ./manage.py createsuperuser"

    Instead, it is recommended to setup Shibboleth or Social Auth and login your first admin.
    After that, you can make an existing user a superuser:

        sudo -Hu aplus sh -c "cd /srv/aplus/a-plus;
          ../venv/bin/python3 ./manage.py set_superuser"

    **NOTE:** You might need to use `--first-name`, `--last-name` or `--email` to limit the number of users.

 1. Create privacy notices

    Copy privacy notice templates

        sudo -Hu aplus sh -c "
          mkdir -p /srv/aplus/a-plus/local_templates/
          cp /srv/aplus/a-plus/templates/privacy_notice_* \
             /srv/aplus/a-plus/local_templates/
        "

    Edit your local templates in `/srv/aplus/a-plus/local_templates/` to match your local information.
