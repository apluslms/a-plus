####
# Default settings for A+ Django project. You should create
# local_settings.py to override any settings like
# SECRET_KEY, DEBUG and DATABASES.
##
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Critical (override in local_settings.py)
# SECURITY WARNING: set debug to false and change production secret key
##########################################################################
DEBUG = True
SECRET_KEY = '&lr5&01mgf9+=!7%rz1&0pfff&oy_uy(8%c8&l+c(kxt&=u87d'
ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)
#SERVER_EMAIL = 'root@'
##########################################################################

ALLOWED_HOSTS = ["*"]
TEMPLATE_DEBUG = DEBUG

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

    # 3rd party applications
    'bootstrapform',
    'tastypie',

    # First party applications
    'inheritance',
    'userprofile',
    'course',
    'exercise',
    'edit_course',
    'deviations',
    'notification',
    'external_services',
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

FILE_UPLOAD_HANDLERS = (
    #"django.core.files.uploadhandler.MemoryFileUploadHandler",
    "django.core.files.uploadhandler.TemporaryFileUploadHandler",
)

ROOT_URLCONF = 'a-plus.urls'
LOGIN_REDIRECT_URL = "/"
LOGIN_ERROR_URL = "/accounts/login/"

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

# Internationalization (may override in local_settings.py)
# https://docs.djangoproject.com/en/1.7/topics/i18n/
LANGUAGE_CODE = 'en-gb'
LANGUAGES = [
    ('en', 'English'),
]
TIME_ZONE = 'EET'
USE_I18N = True
USE_L10N = True
USE_TZ = True
FORMAT_MODULE_PATH = 'a-plus'
LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'locale'),
)

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

INSTALLED_APPS = INSTALLED_LOGIN_APPS + INSTALLED_APPS

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
)
if 'shibboleth_login' in INSTALLED_APPS:
    AUTHENTICATION_BACKENDS += ('shibboleth_login.auth_backend.ShibbolethAuthBackend',)
if 'social.apps.django_app.default' in INSTALLED_APPS:
    AUTHENTICATION_BACKENDS += ('social.backends.google.GoogleOAuth2',)
