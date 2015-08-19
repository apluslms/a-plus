####
# Default settings for A+ Django project. You should create
# local_settings.py in the same directory to override necessary
# settings like SECRET_KEY, DEBUG and DATABASES.
##

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)
#SERVER_EMAIL = 'root@'

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '&lr5&01mgf9+=!7%rz1&0pfff&oy_uy(8%c8&l+c(kxt&=u87d'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = DEBUG

ALLOWED_HOSTS = ["*"]

# Content
# To disable Shibboleth login, comment out 'shibboleth_login' in
# INSTALLED_APPS. Any templates can be overridden by copying into
# local_templates/possible_path/template_name.html

WELCOME_TEXT = 'Welcome to A+ <small>the interoperable e-learning platform</small>'
LOGIN_TITLE_TEXT = 'Local A+ users'
LOGIN_BODY_TEXT = ''
SHIBBOLETH_TITLE_TEXT = 'Aalto university students'
SHIBBOLETH_BODY_TEXT = 'Click the button below to log in with Aalto University\'s identity service.'
SHIBBOLETH_BUTTON_TEXT = 'Aalto WebLogin'
from .privacy_policy import PRIVACY_POLICY_TEXT

# Application definition

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.auth',
    'bootstrapform',
    'tastypie',

    # First party applications
    'inheritance',
    'userprofile',
    'shibboleth_login',
    'course',
    'exercise',
    'edit_course',
    'deviations',
    'notification',
    'external_services',
    'apps',
    'redirect_old_urls',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'lib.middleware.SqlInjectionMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

TEMPLATE_DIRS = (
    os.path.join(BASE_DIR, 'local_templates'),
    os.path.join(BASE_DIR, 'templates'),
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.contrib.messages.context_processors.messages",
)

AUTHENTICATION_BACKENDS = (
    'shibboleth_login.auth_backend.ShibbolethAuthBackend',
    'django.contrib.auth.backends.ModelBackend',
)

FILE_UPLOAD_HANDLERS = (
    #"django.core.files.uploadhandler.MemoryFileUploadHandler",
    "django.core.files.uploadhandler.TemporaryFileUploadHandler",
)

ROOT_URLCONF = 'a-plus.urls'

LOGIN_REDIRECT_URL = "/"

# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

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

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'EET'

USE_I18N = True

USE_L10N = True

USE_TZ = True

#DATETIME_FORMAT = "Y-m-d H:i"

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

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'assets'),
)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Testing
# https://docs.djangoproject.com/en/1.7/topics/testing/advanced/

TEST_RUNNER = "xmlrunner.extra.djangotestrunner.XMLTestRunner"
TEST_OUTPUT_VERBOSE = True
TEST_OUTPUT_DESCRIPTIONS = True
TEST_OUTPUT_DIR = "test_results"

# Logging
# https://docs.djangoproject.com/en/1.7/topics/logging/

LOGGING = {
  'version': 1,
  'disable_existing_loggers': False,
  'formatters': {
    'verbose': {
      'format': '[%(asctime)s: %(levelname)s/%(module)s] %(message)s'
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

# Overrides and appends settings defined in local_settings.py
try:
    from local_settings import *
except ImportError:
    pass
