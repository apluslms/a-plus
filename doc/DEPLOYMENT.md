A+ Deployment Instructions
==========================

Walkthrough for Ubuntu on 6/2015
--------------------------------

1. Python 3.4 was not yet a system package, compile from source.

		# For being able to run unit tests.
		sudo apt-get install libsqlite3-dev
		
		wget https://www.python.org/ftp/python/3.4.3/Python-3.4.3.tar.xz
		tar xvf Python-3.4.3.tar.xz
		cd Python-3.4.3
		./configure
		make
		sudo make install
	
2. Upgrade pip and get virtualenv.

		sudo pip install --upgrade pip
		sudo pip install virtualenv

3. Create the Django application.

		git clone  https://github.com/Aalto-LeTech/a-plus.git
		
		virtualenv -p python3 venv
		source venv/bin/activate
		pip install -r a-plus/requirements.txt
		
		cd a-plus; ./manage.py test

4. Add Postgre SQL database.

		sudo apt-get install postgresql
		sudo -u postgres psql
			create database aplus;
			\c aplus
			create role aplus with superuser;
			grant all privileges on database aplus to [shell-username]
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
		
	You may create local superuser for testing or manual user management.
	
		./manage.py createsuperuser

7. Install uWSGI server, pip install for correct Python version.

		source venv/bin/activate
		pip install uwsgi
		
		sudo mkdir /etc/uwsgi
		sudo mkdir /var/log/uwsgi

8. Configure uWSGI.

	Add file `/etc/uwsgi/aplus.ini`:
	
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
		
		exec uwsgi --emperor /etc/uwsgi
	
	Operate with:
	
		sudo status uwsgi
		sudo start uwsgi
		
	Force application reload with:
	
		sudo touch /etc/uwsgi/aplus.ini

9. Install Apache and libraries.

		sudo apt-get install apache2 libapache2-mod-uwsgi
		sudo a2enmod uwsgi
		
	If used, install Shibboleth middleware and configure for your IDP in `/etc/shibboleth`.
	
		sudo apt-get install libshibsp5 libapache2-mod-shib2	
		sudo a2enmod shib2

10. Configure Apache.

		sudo touch /etc/apache2/sites-available/aplus-ssl
		cd /etc/apache2/sites-enabled
		sudo ln -s ../sites-available/aplus-ssl 000-aplus-ssl
		
	Edit `000-plus-ssl`:
	
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
			<Directory /home/[shell-username]/a-plus/static/>
				Options FollowSymLinks
				Order allow,deny
				Allow from all
			</Directory>
		
			# Mapping to Python WSGI server.
			<Location />
				Options FollowSymLinks
				SetHandler uwsgi-handler
				uWSGISocket 127.0.0.1:3031
			</Location>
			<Location /static/>
				SetHandler None
			</Location>
			<Location /favicon.ico>
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
