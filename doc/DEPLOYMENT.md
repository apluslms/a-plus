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

Aalto University is currently running following combinations on Ubuntu 20.04 or Ubuntu 18.04:

* Apache, uWSGI protocol, uWSGI, Shibboleth, uWSGI logs written to a file
* NGINX, HTTP proxy, gunicorn, Shibboleth, Gunicorn logs written to journald
* NGINX, uWSGI protocol, uWSGI, uWSGI logs written to journald


Table of contents
-----------------

- [A+ Deployment Instructions](#a-deployment-instructions)
  - [Table of contents](#table-of-contents)
  - [Common system configuration](#common-system-configuration)
  - [The Application](#the-application)
  - [Common Shibboleth configuration](#common-shibboleth-configuration)
    - [Key generation](#key-generation)
  - [Apache 2 configuration](#apache-2-configuration)
    - [Shibboleth with Apache 2](#shibboleth-with-apache-2)
  - [NGINX configuration](#nginx-configuration)
    - [Shibboleth with NGINX](#shibboleth-with-nginx)
  - [Final steps](#final-steps)


Common system configuration
---------------------------

 1. Install required packages

        sudo apt-get install \
          git gettext \
          postgresql libpq-dev memcached \
          python3-virtualenv \
          python3-certifi python3-lz4 python3-reportlab python3-reportlab-accel \
          build-essential libxml2-dev libxslt-dev python3-dev python3-venv \
          libpcre3 libpcre3-dev

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

 1. Create RSA keys for [JWT authentication](AUTH.md)

        # generate private key
        openssl genrsa -out private.pem 2048
        # extract public key
        openssl rsa -in private.pem -out public.pem -pubout

The Application
---------------

 1. Change to our service user

        sudo -u aplus -Hi

 1. Clone the Django application

        # as user aplus in /srv/aplus
        git clone --branch production https://github.com/apluslms/a-plus.git
        mkdir a-plus/static \
              a-plus/media

 1. Install virtualenv

        # as user aplus in /srv/aplus
        python3 -m venv venv
        source ~/venv/bin/activate
        pip install -r a-plus/requirements_prod.txt
        pip install -r a-plus/requirements.txt

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
            'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
            'LOCATION': '127.0.0.1:11211',
          }
        }
        ## Session
        SESSION_ENGINE = "django.contrib.sessions.backends.cache"
        SESSION_COOKIE_SECURE = True
        EOF

    Define the branding settings in `aplus/local_settings.py`:
    `BRAND_NAME`, `BRAND_INSTITUTION_NAME`, `BRAND_INSTITUTION_NAME_FI`, etc.
    Check `settings.py` and `local_settings.example.py`.

    Ensure that you use `DEBUG = False` in production (`local_setting.py`).

    Fill the `APLUS_AUTH`, `ALIAS_TO_PUBLIC_KEY` and `URL_TO_ALIAS` settings.
    Check `settings.py` and `local_settings.example.py`.

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
        cp ~/a-plus/doc/uwsgi-aplus-*.ini ~

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


### Key generation

Here is a command to create `sp-key.pem` and `sp-cert.pem` files.
As of writing, `shib-keygen` does create too small keys and uses sha1 for hashing.
Due to security considerations, you should use following instead:

    # set your domain here and then copy-paste command below
    host=$(hostname)
    entityid=https://$host

    cd /etc/shibboleth
    printf '[req]\ndistinguished_name=req\n[san]\nsubjectAltName=DNS:%s, URI:%s\n' "$host" "$entityid" | \
    openssl req -x509 -sha256 -nodes \
      -newkey rsa:4096 -keyout sp-key.pem \
      -days 3650 -out sp-cert.pem \
      -subj "/CN=$host" -extensions san -config /dev/stdin
    chown _shibd:_shibd sp-cert.pem sp-key.pem
    chmod 0400 sp-key.pem

You can print the certificate information with this command:

    openssl x509 -in /etc/shibboleth/sp-cert.pem -noout -text


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
        sudo a2enmod rewrite
        sudo a2dissite 000-default

 1. Create systemd service files for uWSGI processes

        sudo cp /srv/aplus/a-plus/doc/apache2/aplus-*-uwsgi.service \
                /etc/systemd/system
        sudo systemctl daemon-reload
        sudo systemctl enable aplus-web-uwsgi.service aplus-api-uwsgi.service
        sudo systemctl start aplus-web-uwsgi.service aplus-api-uwsgi.service

 1. Reload Apache 2

        sudo systemctl restart apache2.service


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
    Most of the values are common, so only defining `PREFIX` should be enough.
    Currently, `STUDENT_DOMAIN` is a required variable, as A+ presumes student numbers to be from a single domain.
    Rest of the options are documented in `settings.py`.

        sudo tee -a /srv/aplus/a-plus/aplus/local_settings.py << EOF
        # Shibboleth
        SHIBBOLETH_ENVIRONMENT_VARS = {
            'PREFIX': 'SHIB_',
            'STUDENT_DOMAIN': 'example.com', # XXX: change this!
        }
        EOF

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
        openssl dhparam -out /etc/nginx/dhparams.pem 4096

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

 1. Starting from Ubuntu Bionic or NGINX 1.11 we can use dynamic modules

        # as root
        cd /usr/src

        # edit /etc/apt/sources.list if necessary, make sure to enable the
        # -updates repository to get the latest version
        apt-get install build-essential devscripts libnginx-mod-http-headers-more-filter
        apt-get source nginx
        apt-get build-dep nginx

        git clone https://github.com/nginx-shib/nginx-http-shibboleth.git

        pushd nginx-1.*/
        # The module has to be configured using the same arguments as nginx
        NGINX_CONFIGURE_FLAGS=$(nginx -V 2>&1 | grep configure\ arguments | \
          sed 's/configure arguments: //')
        eval $(echo ./configure \
          --add-dynamic-module=../nginx-http-shibboleth \
          $NGINX_CONFIGURE_FLAGS)
        make modules -j$(nproc)
        chmod 644 objs/ngx_http_shibboleth_module.so
        mkdir -p /usr/local/lib/nginx/modules
        cp objs/ngx_http_shibboleth_module.so /usr/local/lib/nginx/modules
        echo "load_module /usr/local/lib/nginx/modules/ngx_http_shibboleth_module.so;" > \
          /etc/nginx/modules-available/50-mod-http-shibboleth.conf
        ln -s ../modules-available/50-mod-http-shibboleth.conf /etc/nginx/modules-enabled/50-mod-http-shibboleth.conf
        systemctl restart nginx

 1. **Obsolete:** With Ubuntu xenial or before NGINX 1.11

    With Ubuntu xenial (16.04) and before NGINX 1.11, dynamic modules are not supported, so you need to rebuild the whole NGINX package.

        sudo -i
        cd /usr/src

        apt-get install build-essential devscripts
        apt-get source nginx
        apt-get build-dep nginx

        git clone https://github.com/nginx-shib/nginx-http-shibboleth.git

        pushd nginx-1.*/

        # add shib module to be build: debian/rules
        patch -l -p1 <<PATCH
        --- a/debian/rules
        +++ b/debian/rules
        @@ -98,6 +98,8 @@
           --with-mail \\
           --with-mail_ssl_module \\
           --with-threads \\
        +  --add-module=\$(MODULESDIR)/headers-more-nginx-module \\
        +  --add-module=/usr/src/nginx-http-shibboleth/ \\
           --add-module=\$(MODULESDIR)/nginx-auth-pam \\
           --add-module=\$(MODULESDIR)/nginx-dav-ext-module \\
           --add-module=\$(MODULESDIR)/nginx-echo \\
        @@ -126,6 +128,7 @@
           --with-stream_ssl_module \\
           --with-threads \\
           --add-module=\$(MODULESDIR)/headers-more-nginx-module \\
        +  --add-module=/usr/src/nginx-http-shibboleth/ \\
           --add-module=\$(MODULESDIR)/nginx-auth-pam \\
           --add-module=\$(MODULESDIR)/nginx-cache-purge \\
           --add-module=\$(MODULESDIR)/nginx-dav-ext-module \\
        PATCH

        # Create debian release
        dch -lshib "Add Shibboleth"
        dch -r ""

        # build debian packages
        dpkg-buildpackage -uc -us
        popd

        # install the packages
        dpkg -i $(ls nginx-common_*shib*_all.deb | sort | tail -n1) \
                $(ls nginx-full_*shib*_amd64.deb | sort | tail -n1)

        exit # exit sudo session

 1. Get NGINX supporting files

        cd /etc/nginx
        wget https://raw.githubusercontent.com/nginx-shib/nginx-http-shibboleth/master/includes/shib_clear_headers

 1. Install required packages

        sudo apt-get install \
          shibboleth-sp-common \
          shibboleth-sp-utils \
          xmltooling-schemas

 1. Create systemd services and sockets for shibboleth scripts

        sudo cp /srv/aplus/a-plus/doc/nginx/shib*.socket \
                /srv/aplus/a-plus/doc/nginx/shib*.service \
                /etc/systemd/system
        sudo systemctl daemon-reload
        sudo systemctl enable shibauthorizer.socket shibresponder.socket
        sudo systemctl start shibauthorizer.socket shibresponder.socket

 1. Configure Shibboleth for your federation or organization

    Configuration is under directory `/etc/shibboleth`.
    For [HAKA](https://wiki.eduuni.fi/display/CSCHAKA/Federation), there is [nginx/shibboleth2.xml](nginx/shibboleth2.xml).

 1. Shibboleth configuration in The `local_settings.py`

    Map your federations variables to ones used in A+.
    Most of the values are common, so only defining `PREFIX` should be enough.
    Currently, `STUDENT_DOMAIN` is a required variable, as A+ presumes student numbers to be from a single domain.
    Rest of the options are documented in `settings.py`.

        sudo tee -a /srv/aplus/a-plus/aplus/local_settings.py << EOF
        # Shibboleth
        SHIBBOLETH_ENVIRONMENT_VARS = {
            'PREFIX': 'HTTP_SHIB_',
            'STUDENT_DOMAIN': 'example.com', # XXX: change this!
        }
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

 1. Create privacy notice, accessibility statement and support page.

    Copy privacy notice, accessibility statement and support page templates.

        sudo -Hu aplus sh -c "
          mkdir -p /srv/aplus/a-plus/local_templates/
          cp /srv/aplus/a-plus/templates/privacy_notice_* \
             /srv/aplus/a-plus/local_templates/
          cp /srv/aplus/a-plus/templates/institution_accessibility_text* \
             /srv/aplus/a-plus/local_templates/
          cp /srv/aplus/a-plus/templates/support_channels* \
             /srv/aplus/a-plus/local_templates/
        "

    Edit your local templates in `/srv/aplus/a-plus/local_templates/` to match your local information.
    If you want to translate the content to different languages, you can use language suffixes in the filenames.
    For example, you can create the following files for the local support page in English and Finnish.

    * `local_templates/support_channels_en.html`
    * `local_templates/support_channels_fi.html`

