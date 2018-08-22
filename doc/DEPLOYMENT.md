A+ Deployment Instructions
==========================

Walkthrough for Ubuntu
----------------------

		$ lsb_release -a
		No LSB modules are available.
		Distributor ID:	Ubuntu
		Description:	Ubuntu 16.04.1 LTS
		Release:	16.04
		Codename:	xenial

1. Currently A+ is stuck with Python 3.4.3
	due to stuck with Django 1.7
	due to django.contrib.contenttypes dependency in ModelWithInheritance
	(TODO: drop the model inheritance completely)

		sudo apt-get install build-essential libssl-dev libsqlite3-dev
		wget https://www.python.org/ftp/python/3.4.3/Python-3.4.3.tar.xz
		tar xvf Python-3.4.3.tar.xz
		cd Python-3.4.3
		./configure
		make
		sudo make install

2. Upgrade pip and get virtualenv.

		sudo pip3 install --upgrade pip
		sudo pip3 install virtualenv

3. Clone the Django application.

	Preferably as a custom user:

		sudo useradd -mUrd /srv/aplus aplus
		sudo su aplus
		cd

		git clone  https://github.com/Aalto-LeTech/a-plus.git

		virtualenv -p python3 venv
		source venv/bin/activate
		pip install -r a-plus/requirements.txt

		cd a-plus
		mkdir media

4. Add Postgre SQL database.

		sudo apt-get install postgresql postgresql-server-dev-all
		sudo -u postgres psql
			create database aplus;
			\c aplus
			create role aplus with login;
			grant all privileges on database aplus to aplus;
			\q

		source venv/bin/activate
		pip install psycopg2

5. Add memcached for superior performance.

		sudo apt-get install memcached
		source venv/bin/activate
		pip install python-memcached

5. Configure Django.

	Add file (to project root) `/srv/aplus/a-plus/local_settings.py`:

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

		CACHES = {
			'default': {
				'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
				'LOCATION': '127.0.0.1:11211',
			}
		}

		DEBUG = False
		ALLOWED_HOSTS = ['*']

6. Create database tables.

		source venv/bin/activate
		cd a-plus; ./manage.py migrate

		# You may create local superuser for testing or manual user management.
		./manage.py createsuperuser

7. Compile localisation files

        source venv/bin/activate
        cd a-plus; ./manage.py compilemessages

7. Collect static files for serving via Apache.

		source venv/bin/activate
		cd a-plus; ./manage.py collectstatic

8. Install uWSGI server, pip install for correct Python version.

		source venv/bin/activate
		pip install uwsgi

9. Configure uWSGI.

		sudo mkdir /var/log/uwsgi
		sudo touch /var/log/uwsgi/aplus.log
		sudo chown aplus:aplus /var/log/uwsgi/aplus.log
		sudo mkdir -p /etc/uwsgi/apps-enabled
		cd /etc/uwsgi/apps-enabled
		sudo mkdir ../apps-available
		sudo touch ../apps-available/aplus.ini
		sudo ln -s ../apps-available/aplus.ini .

	Edit file `aplus.ini`:

		[uwsgi]
		chdir=/srv/aplus/a-plus
		module=aplus.wsgi:application
		home=/srv/aplus/venv
		master=True
		uid=aplus
		gid=aplus
		daemonize=/var/log/uwsgi/aplus.log
		socket=127.0.0.1:3031

	Ubuntu systemd, Add file `/lib/systemd/system/uwsgi.service`:

		[Unit]
		Description=uWSGI Python Web Server

		[Service]
		Type=simple
		ExecStart=/srv/aplus/venv/bin/uwsgi --emperor /etc/uwsgi/apps-enabled

		[Install]
		WantedBy=multi-user.target

	Ubuntu systemd, Operate with:

		sudo systemctl status uwsgi
		sudo systemctl start uwsgi
		sudo systemctl restart uwsgi

	*DEPRECATED Ubuntu upstart*, Add file `/etc/init/uwsgi.conf`:

		description "uWSGI Python Web Server"
		start on runlevel [2345]
		stop on runlevel [06]

		respawn

		exec /home/[shell-username]/venv/bin/uwsgi --emperor /etc/uwsgi/apps-enabled

	*DEPRECATED Ubuntu upstart*, Operate with:

		sudo status uwsgi
		sudo start uwsgi

	Discreet application reload that does not break connections
	(make sure uwsgi has write access to the log file)

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

		sudo touch /etc/apache2/sites-available/aplus-ssl.conf
		cd /etc/apache2/sites-enabled
		sudo ln -s ../sites-available/aplus-ssl.conf 000-aplus-ssl.conf

	Edit `000-aplus-ssl.conf`:

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
			SSLCertificateChainFile /etc/ssl/certs/aplus.chain.pem

			# Static files served by Apache.
			Alias /static/ /srv/aplus/a-plus/static/
			Alias /favicon.ico /srv/aplus/a-plus/static/favicons/favicon.ico
			AliasMatch ^/media/public/(.*)$ /srv/aplus/a-plus/media/public/$1
			<Directory /srv/aplus/a-plus/static/>
				# Deprecated Apache 2.2
				# Order allow,deny
				# Allow from all
				Require all granted
			</Directory>
			<Directory /srv/aplus/a-plus/media/public/>
				Require all granted
			</Directory>

			# Mapping to Python WSGI server.
			<Location />
				DirectoryIndex disabled
				Options -Indexes
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
		sudo systemctl restart uwsgi
		sudo /etc/init.d/apache2 restart
