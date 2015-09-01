A+ Deployment Instructions
==========================

Walkthrough for Ubuntu on 6/2015
--------------------------------

1. Python 3.4 was not yet a system package, compile from source.

		sudo apt-get install libsqlite3-dev
		wget https://www.python.org/ftp/python/3.4.3/Python-3.4.3.tar.xz
		tar xvf Python-3.4.3.tar.xz
		cd Python-3.4.3
		./configure
		make
		sudo make install

2. Upgrade pip and get virtualenv.

		sudo pip3 install --upgrade pip
		sudo pip3 install virtualenv

3. Create the Django application.

		git clone  https://github.com/Aalto-LeTech/a-plus.git

		virtualenv -p python3 venv
		source venv/bin/activate
		pip install -r a-plus/requirements.txt

		cd a-plus; ./manage.py test

4. Add Postgre SQL database.

		sudo apt-get install postgresql postgresql-server-dev-all
		sudo -u postgres psql
			create database aplus;
			\c aplus
			create role [shell-username] with login;
			grant all privileges on database aplus to [shell-username];
			\q

		source venv/bin/activate
		pip install psycopg2

5. Configure Django.

	Add file (to project root) `/home/[shell-username]/a-plus/local_settings.py`:

		ADMINS = (
			('My Name', 'my.name@domain.org'),
		)
		SERVER_EMAIL = 'root@aplus.domain.org'

		SECRET_KEY = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

		DATABASES = {
			'default': {
				'ENGINE': 'django.db.backends.postgresql_psycopg2',
				'NAME': 'aplus',
			}
		}

		DEBUG = False
		ALLOWED_HOSTS = ['*']

6. Create database tables.

		source venv/bin/activate
		cd a-plus; ./manage.py migrate

		# You may create local superuser for testing or manual user management.
		./manage.py createsuperuser

7. Collect static files for serving via Apache.

		source venv/bin/activate
		cd a-plus; ./manage.py collectstatic

8. Install uWSGI server, pip install for correct Python version.

		source venv/bin/activate
		pip install uwsgi

9. Configure uWSGI.

		sudo mkdir /var/log/uwsgi
		sudo mkdir -p /etc/uwsgi/apps-enabled
		cd /etc/uwsgi/apps-enabled
		sudo mkdir ../apps-available
		sudo touch ../apps-available/aplus.ini
		sudo ln -s ../apps-available/aplus.ini .

	Edit file `aplus.ini`:

		[uwsgi]
		chdir=/home/[shell-username]/a-plus
		module=a-plus.wsgi:application
		home=/home/[shell-username]/venv
		master=True
		uid=[shell-username]
		gid=[shell-username]
		daemonize=/var/log/uwsgi/aplus.log
		socket=127.0.0.1:3031

	Add file `/etc/init/uwsgi.conf`:

		description "uWSGI Python Web Server"
		start on runlevel [2345]
		stop on runlevel [06]

		respawn

		exec /home/[shell-username]/venv/bin/uwsgi --emperor /etc/uwsgi/apps-enabled

	Operate with:

		sudo status uwsgi
		sudo start uwsgi

		# Force application reload with
		sudo touch /etc/uwsgi/apps-enabled/aplus.ini

10. Install Apache and libraries.

		sudo apt-get install apache2 libapache2-mod-uwsgi
		sudo a2enmod uwsgi

	If used, install Shibboleth middleware and configure for your IDP in `/etc/shibboleth`.

		sudo apt-get install libshibsp5 libapache2-mod-shib2
		sudo a2enmod shib2

	The `local_settings.py` supports following Shibboleth configuration.

		# Apache module mod_uwsgi was unable to create UTF-8 environment variables.
		# Problem was avoided by URL encoding in Shibboleth: <RequestMap encoding="URL" />
		SHIBBOLETH_VARIABLES_URL_ENCODED = True

		# Set the Shibboleth environment variable names (defaults given here).
		SHIB_USER_ID_KEY = 'SHIB_eppn'
		SHIB_FIRST_NAME_KEY = 'SHIB_displayName'
		SHIB_LAST_NAME_KEY = 'SHIB_sn'
		SHIB_MAIL_KEY = 'SHIB_mail'
		SHIB_STUDENT_ID_KEY = 'SHIB_schacPersonalUniqueCode'

11. Configure Apache.

		sudo touch /etc/apache2/sites-available/aplus-ssl
		cd /etc/apache2/sites-enabled
		sudo ln -s ../sites-available/aplus-ssl 000-aplus-ssl

	Edit `000-aplus-ssl`:

		<IfModule mod_ssl.c>
		<VirtualHost _default_:443>
			ServerAdmin root@aplus.domain.org
			ServerName aplus.domain.org
			UseCanonicalName On

			ErrorLog ${APACHE_LOG_DIR}/aplus_error.log
			LogLevel warn
			CustomLog ${APACHE_LOG_DIR}/aplus_access.log combined

			SSLEngine on
			SSLCertificateFile    /etc/ssl/certs/aplus.domain.org.pem
			SSLCertificateKeyFile /etc/ssl/private/aplus.domain.org.key
			SSLCertificateChainFile /etc/apache2/ssl.crt/terena_chain.pem

			# Static files served by Apache.
			Alias /static/ /home/[shell-username]/a-plus/static/
			Alias /favicon.ico /home/[shell-username]/a-plus/static/favicons/favicon.ico
			AliasMatch ^/media/public/(.*)$ /home/[shell-username]/a-plus/media/public/$1
			<Directory /home/[shell-username]/a-plus/static/>
				Order allow,deny
				Allow from all
			</Directory>
			<Directory /home/[shell-username]/a-plus/media/public/>
				Order allow,deny
				Allow from all
			</Directory>

			# Mapping to Python WSGI server.
			<Location />
				Options FollowSymLinks
				SetHandler uwsgi-handler
				uWSGISocket 127.0.0.1:3031
				uWSGIMaxVars 256
			</Location>
			<Location /static/>
				SetHandler None
			</Location>
			<Location /favicon.ico>
				SetHandler None
			</Location>
			<Location /media/public/>
				SetHandler None
			</Location>

			# Mapping and authentication for Shibboleth middleware.
			<IfModule mod_shib_22.c>
				<Location /Shibboleth.sso>
					SetHandler shib
				</Location>
				<Location /shibboleth>
					AuthType shibboleth
					Require valid-user
					ShibRequireSession On
				</Location>
			</IfModule>

		</VirtualHost>
		</IfModule>

12. Run it all.

		sudo /etc/init.d/shibd restart
		sudo restart uwsgi
		sudo /etc/init.d/apache2 restart
