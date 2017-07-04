####
# Default settings for A+ Django project. You should create
# local_settings.py to override any settings like
# SECRET_KEY, DEBUG and DATABASES.
##
import os, warnings
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Critical (override in local_settings.py)
# SECURITY WARNING: set debug to false and change production secret key
##########################################################################
DEBUG = True
SECRET_KEY = None
ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)
#SERVER_EMAIL = 'root@'
ALLOWED_HOSTS = ["*"]
##########################################################################


# Content (may override in local_settings.py)
#
# Any templates can be overridden by copying into
# local_templates/possible_path/template_name.html
##########################################################################
SITEWIDE_ALERT_TEXT = None
BRAND_NAME = 'A+'

WELCOME_TEXT = 'Welcome to A+ <small>modern learning environment</small>'
SHIBBOLETH_TITLE_TEXT = 'Aalto University users'
SHIBBOLETH_BODY_TEXT = 'Log in with Aalto University user account by clicking the button below. Programme students and faculty must login here.'
SHIBBOLETH_BUTTON_TEXT = 'Aalto Login'
MOOC_TITLE_TEXT = 'Users external to Aalto'
MOOC_BODY_TEXT = 'Some of our courses are open for everyone. Login with your user account from one of the following services.'
LOGIN_TITLE_TEXT = ''
LOGIN_BODY_TEXT = ''
LOGIN_BUTTON_TEXT = 'Maintenance login'
INTERNAL_USER_LABEL = 'Aalto'
EXTERNAL_USER_LABEL = 'MOOC'

WELCOME_TEXT_FI = 'A+ <small>verkkopohjainen oppimisympäristö</small>'
SHIBBOLETH_TITLE_TEXT_FI = 'Aalto-yliopiston käyttäjät'
SHIBBOLETH_BODY_TEXT_FI = 'Kirjaudu palveluun Aalto-yliopiston käyttäjätunnuksella alla olevasta painikkeesta. Koulutusohjelmien opiskelijoiden ja henkilökunnan pitää kirjautua tästä.'
SHIBBOLETH_BUTTON_TEXT_FI = 'Aalto-kirjautuminen'
MOOC_TITLE_TEXT_FI = 'Käyttäjät Aallon ulkopuolelta'
MOOC_BODY_TEXT_FI = 'Osa kursseistamme on avoinna kaikille. Kirjaudu sisään jonkin seuraavan palvelun käyttäjätunnuksellasi.'
LOGIN_TITLE_TEXT_FI = ''
LOGIN_BODY_TEXT_FI = ''
LOGIN_BUTTON_TEXT_FI = 'Ylläpidon kirjautuminen'

TRACKING_HTML = ''

from .privacy_policy import PRIVACY_POLICY_TEXT, PRIVACY_POLICY_TEXT_FI
##########################################################################

# Exercise loading settings
EXERCISE_HTTP_TIMEOUT = 15
EXERCISE_HTTP_RETRIES = (5,5,5)
EXERCISE_ERROR_SUBJECT = """A+ exercise error in {course}: {exercise}"""
EXERCISE_ERROR_DESCRIPTION = """
As a course teacher or technical contact you were automatically emailed by A+ about the error incident. A student could not access or submit an exercise because the grading service used is offline or unable to produce valid response.

{message}

Open the exercise:
  {exercise_url}
Edit course email settings:
  {course_edit_url}

****************************************
Error trace:
****************************************

{error_trace}

****************************************
Request fields:
****************************************

{request_fields}
"""

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.humanize',

    # 3rd party applications
    'bootstrapform',
    'rest_framework',
    'rest_framework.authtoken',

    # First party applications
    'inheritance',
    'userprofile',
    'authorization',
    'course',
    'exercise',
    'edit_course',
    'deviations',
    'notification',
    'external_services',
    'news',
    'threshold',
    'diploma',
    'apps',
    'redirect_old_urls',
)

# Different login options (may override in local_settings.py)
##########################################################################
INSTALLED_LOGIN_APPS = (
    'shibboleth_login',
    #'social.apps.django_app.default',
)

# Apache module mod_uwsgi was unable to create UTF-8 environment variables.
# Problem was avoided by URL encoding in Shibboleth:
# <RequestMapper type="Native">
#   <RequestMap applicationId="default" encoding="URL" />
# </RequestMapper>
SHIBBOLETH_VARIABLES_URL_ENCODED = True

# Fields to receive from the Shibboleth (defaults).
#SHIB_USER_ID_KEY = 'SHIB_eppn'
#SHIB_FIRST_NAME_KEY = 'SHIB_displayName'
#SHIB_LAST_NAME_KEY = 'SHIB_sn'
#SHIB_MAIL_KEY = 'SHIB_mail'
#SHIB_STUDENT_ID_KEY = 'SHIB_schacPersonalUniqueCode'

# Google OAuth2 settings
#SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = ''
#SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = ''
SOCIAL_AUTH_GOOGLE_OAUTH2_USE_DEPRECATED_API = True
SOCIAL_AUTH_USERNAME_IS_FULL_EMAIL = True
##########################################################################

MIDDLEWARE_CLASSES = (
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'lib.middleware.SqlInjectionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'social.apps.django_app.middleware.SocialAuthExceptionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'aplus.urls'
LOGIN_REDIRECT_URL = "/"
LOGIN_ERROR_URL = "/accounts/login/"

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'local_templates'),
            os.path.join(BASE_DIR, 'templates'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                'django.template.context_processors.request',
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

FILE_UPLOAD_HANDLERS = (
    #"django.core.files.uploadhandler.MemoryFileUploadHandler",
    "django.core.files.uploadhandler.TemporaryFileUploadHandler",
)

WSGI_APPLICATION = 'aplus.wsgi.application'


# Database (override in local_settings.py)
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases
##########################################################################
DATABASE_FILE = os.environ.get('APLUS_DB_FILE', default='aplus.db')
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': os.path.join(BASE_DIR, DATABASE_FILE), # Or path to database file if using sqlite3.
        'USER': '', # Not used with sqlite3.
        'PASSWORD': '', # Not used with sqlite3.
        'HOST': '', # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '', # Set to empty string for default. Not used with sqlite3.
    }
}
##########################################################################

# Cache (override in local_settings.py)
# https://docs.djangoproject.com/en/1.10/topics/cache
##########################################################################
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        #'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        #'LOCATION': '127.0.0.1:11211',
        'TIMEOUT': None,
    }
}
#SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
##########################################################################

# Internationalization (may override in local_settings.py)
# https://docs.djangoproject.com/en/1.7/topics/i18n/
LANGUAGE_CODE = 'en-gb'
LANGUAGES = [
    ('en', 'English'),
    ('fi', 'Finnish'),
]
TIME_ZONE = 'EET'
USE_I18N = True
USE_L10N = True
USE_TZ = True
FORMAT_MODULE_PATH = 'aplus'
LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'locale'),
)

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/
STATICFILES_STORAGE = 'lib.storage.BumpStaticFilesStorage'
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'assets'),
)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Django REST Framework settings
# http://www.django-rest-framework.org/api-guide/settings/
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        # Clients should use token for authentication
        # Requires rest_framework.authtoken in apps.
        'rest_framework.authentication.TokenAuthentication',
        'lib.api.authentication.grader.GraderAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        # If not other permissions are defined, require login.
        'rest_framework.permissions.IsAuthenticated',
        'userprofile.permissions.GraderUserCanOnlyRead',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'lib.api.core.APlusJSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    'DEFAULT_CONTENT_NEGOTIATION_CLASS': 'lib.api.core.APlusContentNegotiation',
    'DEFAULT_VERSIONING_CLASS': 'lib.api.core.APlusVersioning',
    'PAGE_SIZE': 100,
    'DEFAULT_VERSION': '2',
    'ALLOWED_VERSIONS': {
        # These are really just latest versions
        '1': '1.0',
        '2': '2.0',
    },
}

# Testing
# https://docs.djangoproject.com/en/1.7/topics/testing/advanced/
TEST_RUNNER = "xmlrunner.extra.djangotestrunner.XMLTestRunner"
TEST_OUTPUT_VERBOSE = True
TEST_OUTPUT_DESCRIPTIONS = True
TEST_OUTPUT_DIR = "test_results"

# Logging
# https://docs.djangoproject.com/en/1.7/topics/logging/
from lib.logging import skip_unreadable_post
LOGGING = {
  'version': 1,
  'disable_existing_loggers': False,
  'formatters': {
    'verbose': {
      'format': '[%(asctime)s: %(levelname)s/%(module)s] %(message)s'
    },
  },
  'filters': {
    'skip_unreadable_post': {
        '()': 'django.utils.log.CallbackFilter',
        'callback': skip_unreadable_post,
    },
  },
  'handlers': {
    'console': {
      'level': 'DEBUG',
      'class': 'logging.StreamHandler',
      'stream': 'ext://sys.stdout',
      'formatter': 'verbose',
    },
    'email': {
      'level': 'ERROR',
      'filters': ['skip_unreadable_post'],
      'class': 'django.utils.log.AdminEmailHandler',
    },
  },
  'loggers': {
    '': {
      'level': 'INFO',
      'handlers': ['email', 'console'],
      'propagate': True
    },
  },
}





###############################################################################
#
# Settings logic to handle local settings and any reactions to them
#

# Overrides and appends settings defined in local_settings.py
try:
    from local_settings import *
except ImportError:
    try:
        from aplus.local_settings import *
    except ImportError:
        # make a warning that there is no local_settings, but ignore the exception
        warnings.warn("Couldn't find local_settings.py from project root nor under aplus/")
        pass

if not SECRET_KEY:
    try:
        from .secret_key import *
    except ImportError:
        from lib.helpers import create_secret_key_file
        settings_dir = os.path.abspath(os.path.dirname(__file__))
        key_filename = os.path.join(settings_dir, 'secret_key.py')
        create_secret_key_file(key_filename)
        warnings.warn("SECRET_KEY not defined in local_settings.py, created one in %s" % (key_filename,))
        del settings_dir
        del create_secret_key_file
        del key_filename
        from .secret_key import *

INSTALLED_APPS = INSTALLED_LOGIN_APPS + INSTALLED_APPS

SOCIAL_AUTH = False
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
)
if 'shibboleth_login' in INSTALLED_APPS:
    AUTHENTICATION_BACKENDS += ('shibboleth_login.auth_backend.ShibbolethAuthBackend',)
if 'social.apps.django_app.default' in INSTALLED_APPS:
    SOCIAL_AUTH = True
    AUTHENTICATION_BACKENDS += ('social.backends.google.GoogleOAuth2',)

# If debug is enabled allow basic auth for API
if DEBUG:
    REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] += ('rest_framework.authentication.BasicAuthentication',)
else:
    TEMPLATES[0]['OPTIONS']['loaders'] = [
        ('django.template.loaders.cached.Loader', [
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        ]),
    ]
