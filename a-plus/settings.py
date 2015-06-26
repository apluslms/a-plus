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

ALLOWED_HOSTS = []

# Content

WELCOME_TEXT = 'Welcome to A+ <small>the interoperable e-learning platform</small>'

# Application definition

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.auth',

    # Third party applications
    'django_shibboleth', # for shibboleth logins
    'tastypie', # service api

    # First party applications
    'inheritance',
    'userprofile',
    'course',
    'exercise',
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
    #'userprofile.middleware.StudentGroupMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'lib.middleware.SqlInjectionMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

TEMPLATE_DIRS = (
    os.path.join(BASE_DIR, 'templates'),
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.contrib.messages.context_processors.messages",
    #"userprofile.context_processors.student_group",
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
        'NAME': os.path.join(BASE_DIR, DATABASE_FILE),  # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
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

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'assets'),
)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Shibboleth settings
# https://github.com/sorrison/django-shibboleth 

SHIB_ATTRIBUTE_MAP = {
    "HTTP_SHIB_IDENTITY_PROVIDER": (True, "idp"),
    "SHIB_eppn": (True, "eppn"),
    "HTTP_SHIB_CN": (False, "cn"),
    "HTTP_SHIB_DISPLAYNAME": (False, "first_name"),
    "HTTP_SHIB_SN": (False, "last_name"),
    #"HTTP_SHIB_AALTOID": (False, "student_id"),
    "HTTP_SHIB_SCHACPERSONALUNIQUECODE": (False, "student_id"),
    "HTTP_SHIB_MAIL": (False, "email")
}
SHIB_USERNAME = "eppn"
SHIB_EMAIL = "email"
SHIB_FIRST_NAME = "first_name"
SHIB_LAST_NAME = "last_name"

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
  'disable_existing_loggers': True,
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
      'level': 'DEBUG',
      'handlers': ['email', 'console'],
      'propagate': True
    },
    'django': {
      'level': 'INFO',
      'handlers': [],
      'propagate': True
    },
  },
}

# Overrides and appends settings defined in local_settings.py
try:
    from local_settings import *
except ImportError:
    pass
