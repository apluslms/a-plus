####
# Default settings for A+ Django project.
# You should create local_settings.py to override any settings.
# You can copy local_settings.example.py and start from there.
##
from os.path import abspath, dirname, join
from lib.logging import skip_unreadable_post
from os import environ
from r_django_essentials.conf import (
    update_settings_from_environment,
    update_settings_with_file,
    update_secret_from_file,
    use_cache_template_loader_in_production
)
BASE_DIR = dirname(dirname(abspath(__file__)))


# Base options, commonly overridden in local_settings.py
##########################################################################
DEBUG = False
SECRET_KEY = None
ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)
#SERVER_EMAIL = 'root@'
EMAIL_TIMEOUT = 30 # Do not block web workers when email backend is broken
ALLOWED_HOSTS = ["*"]

# The organization this instance is deployed at.
# Can be used to identify users from home university by comparing this to
# organization information received from Haka login.
LOCAL_ORGANIZATION = 'aalto.fi'

# Scheme and host for course materials, e.g., "https://<gitmanager_host>".
GITMANAGER_URL = None

# Authentication and authentication library settings
# see https://pypi.org/project/aplus-auth/ for explanations
APLUS_AUTH_LOCAL = {
    #"UID": "...", # set to "aplus" below, can be changed
    "PRIVATE_KEY": None,
    "PUBLIC_KEY": None,
    "TRUSTING_REMOTES": {
        #"http://example.com": "grader"
        #"http://grader.example.com": "grader2"
        #"https://otherexample.com": "grader2"
        #"onemoreexample.com": "gitmanager"
    },
    #"DEFAULT_AUD_UID": "...", # set to "unknown" below, can be changed
    "UID_TO_KEY": {
        #"grader": <RSA public key of grader>
        #"grader2": <RSA public key of grader2>,
        #"gitmanager": <RSA public key of gitmanager>,
    },
    #"DISABLE_JWT_SIGNING": False,
    #"DISABLE_LOGIN_CHECKS": False,
}
##########################################################################

APLUS_AUTH = {
    "UID": "aplus",
    "DEFAULT_AUD_UID": "unknown",
}

# Expiry time for LTI 1.3 JWT tokens, in seconds
LTI_TOKEN_LIFETIME = 3600

# Content (may override in local_settings.py)
#
# Any templates can be overridden by copying into
# local_templates/possible_path/template_name.html
##########################################################################
SITEWIDE_ALERT_TEXT = None
SITEWIDE_ADVERT = {
   'not-before': '2025-01-01', # start showing on 1st
   'not-after': '2026-01-04', # last visible date is 3rd
   'title': {'en': "Advert", 'fi': "Mainos"},
   'text': {'en': "We have open positions",
            'fi': "Meillä on paikkoja"},
   'href': "https://apluslms.github.io",
   'image': "https://apluslms.github.io/assets/images/apluslogo.png",
}
BRAND_NAME = 'A+'
BRAND_NAME_LONG = 'Aplus'
BRAND_DESCRIPTION = 'Virtual Learning Environment'
BRAND_INSTITUTION_NAME = 'Aalto University'
BRAND_INSTITUTION_NAME_FI = 'Aalto-yliopisto'

WELCOME_TEXT = 'Welcome to A+ <small class="text-body-secondary">modern learning environment</small>'
SHIBBOLETH_TITLE_TEXT = 'Aalto University users'
SHIBBOLETH_BODY_TEXT = (
    'Log in with your Aalto University user account by clicking on the button below. '
    'FiTech, Open University and programme students as well as staff members must log in here.'
)
SHIBBOLETH_BUTTON_TEXT = 'Log in with Aalto account'
HAKA_TITLE_TEXT = 'Haka Federation users'
HAKA_BODY_TEXT = 'If your organization is a member of Haka federation, log in by clicking the button below.'
HAKA_BUTTON_TEXT = 'Log in with Haka'
MOOC_TITLE_TEXT = 'Users external to Aalto'
MOOC_BODY_TEXT = (
    'Some of our courses are open for everyone. '
    'Log in with your user account from one of the following services.'
)
INTERNAL_USER_LABEL = 'Aalto'
EXTERNAL_USER_LABEL = 'MOOC'
LOGIN_USER_DATA_INFO = (
    'Your personal data are stored in {brand_name}. '
    'For additional information, please see <a href="{privacy_url}">the privacy notice</a>.'
)

WELCOME_TEXT_FI = 'A+ <small class="text-body-secondary">verkkopohjainen oppimisympäristö</small>'
SHIBBOLETH_TITLE_TEXT_FI = 'Aalto-yliopiston käyttäjät'
SHIBBOLETH_BODY_TEXT_FI = (
    'Kirjaudu palveluun Aalto-yliopiston käyttäjätunnuksella alla olevasta painikkeesta. '
    'FiTechin, avoimen yliopiston ja koulutusohjelmien opiskelijoiden sekä henkilökunnan täytyy kirjautua tästä.'
)
SHIBBOLETH_BUTTON_TEXT_FI = 'Kirjaudu Aalto-tunnuksella'
HAKA_TITLE_TEXT_FI = 'Haka-käyttäjät'
HAKA_BODY_TEXT_FI = 'Jos organisaatiosi on Haka-federaation jäsen, kirjaudu palveluun alla olevasta painikkeesta.'
HAKA_BUTTON_TEXT_FI = 'Kirjaudu Haka-tunnuksella'
MOOC_TITLE_TEXT_FI = 'Käyttäjät Aallon ulkopuolelta'
MOOC_BODY_TEXT_FI = (
    'Osa kursseistamme on avoinna kaikille. '
    'Kirjaudu sisään jonkin seuraavan palvelun käyttäjätunnuksellasi.'
)
LOGIN_USER_DATA_INFO_FI = (
    'Henkilötietosi säilytetään {brand_name}-järjestelmässä. '
    'Katso lisätietoja <a href="{privacy_url}">tietosuojailmoituksesta</a>.'
)

TRACKING_HTML = ''

EXCEL_CSV_DEFAULT_DELIMITER = ';'
##########################################################################

# Exercise loading settings
EXERCISE_HTTP_TIMEOUT = 15
EXERCISE_HTTP_RETRIES = (5,5,5)
EXERCISE_ERROR_SUBJECT = """A+ exercise error in {course}: {exercise}"""
EXERCISE_ERROR_DESCRIPTION = (
    '\nAs a course teacher or technical contact you were automatically emailed by A+ about the error incident. '
    'A student could not access or submit an exercise because the grading service used is offline '
    'or unable to produce valid response.\n'
    '\n'
    '{message}\n'
    '\n'
    'Open the exercise:\n'
    '  {exercise_url}\n'
    'Edit course email settings:\n'
    '  {course_edit_url}\n'
    '\n'
    '****************************************\n'
    'Error trace:\n'
    '****************************************\n'
    '\n'
    '{error_trace}\n'
    '\n'
    '****************************************\n'
    'Request fields:\n'
    '****************************************\n'
    '\n'
    '{request_fields}\n'
)

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.humanize',
    'django.contrib.sitemaps',
    'django.forms',

    # 3rd party applications
    'django_bootstrap5',
    'rest_framework',
    'rest_framework.authtoken',
    'pylti1p3.contrib.django.lti1p3_tool_config',

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
    'lti_tool',
    'site_alert',

    'js_jquery_toggle',
    'django_colortag',
    'aplus_auth',
)

# Sitemap settings
##########################################################################

# A course is considered recent or upcoming if it was/is open within this delta (in days) from now.
SITEMAP_DELTA_DAYS_RECENT_OR_UPCOMING = 180

# Different login options (may override in local_settings.py)
##########################################################################

## Shibboleth

#INSTALLED_APPS += ('shibboleth_login',)

# Shibboleth Login configs
#SHIBBOLETH_LOGIN = {
#    # users, who do not exists, are created
#    'ALLOW_CREATE_NEW_USERS': True,
#    # if user is not found using USER_ID, then we can try with EMAIL
#    # the search must yield only single user for it to succeed
#    'ALLOW_SEARCH_WITH_EMAIL': False,
#}

# Fields to receive from the Shibboleth (defaults).
#SHIBBOLETH_ENVIRONMENT_VARS = {
#    # Apache module mod_uwsgi is unable to create UTF-8 environment variables.
#    # Problem is avoided by enabling URL encoding in Shibboleth:
#    #   <RequestMapper type="Native">
#    #     <RequestMap applicationId="default" encoding="URL" />
#    #   </RequestMapper>
#    # This is also recommended for nginx
#    'URL_DECODE': True, # set to False, if you are passing values in UTF-8
#    # required:
#    'PREFIX': 'SHIB_',
#    'STUDENT_DOMAIN': 'example.com',  # currently only student numbers from this domain are used
#    # optional:
#    'USER_ID': 'eppn',
#    'FIRST_NAME': 'givenName',
#    'LAST_NAME': 'sn',
#    'COMMON_NAME': 'cn',        # used if first or last name is missing
#    'FULL_NAME': 'displayName', # used if first or last name is missing
#    'EMAIL': 'mail',
#    'STUDENT_IDS': 'schacPersonalUniqueCode',
#    'STUDENT_URN': ':schac:personalUniqueCode:',
#    'STUDENT_FILTERS': {3: 'int', 2: 'studentID'},
#}

## Haka
#HAKA_LOGIN = True


## Google OAuth2 settings

#INSTALLED_APPS += ('social_django',)
#SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = ''
#SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = ''
SOCIAL_AUTH_URL_NAMESPACE = 'social'
SOCIAL_AUTH_USERNAME_IS_FULL_EMAIL = True

##########################################################################¨
# Student Information System plugin settings
#SIS_PLUGIN_MODULE = 'course.sis_test'
#SIS_PLUGIN_CLASS = 'SisTest'

# Set up schedule for periodic student enrollment check for active
# courses with SIS linkage
# See https://docs.celeryproject.org/en/stable/userguide/periodic-tasks.html
# For example:
# from celery.schedules import crontab
# SIS_ENROLL_SCHEDULE = 10.0  -- every 10 seconds
# SIS_ENROLL_SCHEDULE = crontab(hour=1, minute=0) -- every night at 1:00
# If variable is not set, no automatic enrollment takes place

# Delay in seconds between outgoing SIS enrollment requests (None for no delay)
SIS_ENROLL_DELAY = 15

##########################################################################
# Settings related automatic retries of unfinished grading tasks

# Number of seconds after which a submission can be resent to grader, if not completed
# If set to None, retries are disabled.
SUBMISSION_EXPIRY_TIMEOUT = 30 * 60

# List of services with automatic grading where retries are allowed
# Network location is sufficient, e.g. "localhost:8080" or "grader.cs.aalto.fi"
SUBMISSION_RETRY_SERVICES = []

# Maximum number of retries to automatically grade a given submission
SUBMISSION_RETRY_LIMIT = 3

# Number of unresponded retries beyond which we move to recovery state.
# In recovery state there likely is more persistent problem with the grader
# or network that needs fixing.
# In recovery state A+ periodically probes the state of the grader, sending only one
# grading request out every SUBMISSION_EXPIRY_TIMEOUT seconds.
# We do not want to congest the potentially broken system unnecessarily with several
# requests in this case.
GRADER_STABLE_THRESHOLD = 5

## Celery
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_BROKER_URL = 'redis://redis:6379'
CELERY_RESULT_BACKEND = 'redis://redis:6379'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'lib.middleware.LocaleMiddleware',
    'social_django.middleware.SocialAuthExceptionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'lib.request_globals.ClearRequestGlobals'
]

ROOT_URLCONF = 'aplus.urls'
LOGIN_REDIRECT_URL = "/"
LOGIN_ERROR_URL = "/accounts/login/"

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            join(BASE_DIR, 'local_templates'),
            join(BASE_DIR, 'templates'),
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
                "lib.context_processors.aplus_version",
                "lib.context_processors.gitmanager_enabled",
            ],
        },
    },
]
FORM_RENDERER = 'django.forms.renderers.TemplatesSetting'

FILE_UPLOAD_HANDLERS = (
    #"django.core.files.uploadhandler.MemoryFileUploadHandler",
    "django.core.files.uploadhandler.TemporaryFileUploadHandler",
)
FILE_UPLOAD_MAX_MEMORY_SIZE = 10000000
FILE_UPLOAD_PERMISSIONS = 0o644

WSGI_APPLICATION = 'aplus.wsgi.application'


# Database (override in local_settings.py)
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases
##########################################################################
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': join(BASE_DIR, 'aplus.db'), # Or path to database file if using sqlite3.
        'USER': '', # Not used with sqlite3.
        'PASSWORD': '', # Not used with sqlite3.
        'HOST': '', # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '', # Set to empty string for default. Not used with sqlite3.
    }
}
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
##########################################################################

# Cache (override in local_settings.py)
# https://docs.djangoproject.com/en/4.2/topics/cache
# Use PyLibMCCache instead of PyMemcacheCache if using memcached as PyMemcacheCache
# has bad get_many/set_many performance
##########################################################################
CACHES = {
    'default': {
        'BACKEND': 'lib.cache.backends.LocMemCache',
        'TIMEOUT': None,
        'OPTIONS': {'MAX_SIZE': 1000000}, # simulate memcached value limit
    }
}
# The default SESSION_ENGINE is 'django.contrib.sessions.backends.db' (database)
# Cache-based sessions require the Memcached cache backend.
#SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
##########################################################################

# Internationalization (may override in local_settings.py)
# https://docs.djangoproject.com/en/1.7/topics/i18n/
LANGUAGE_CODE = 'en-gb'
LANGUAGES = [
    ('en', 'English'),
    ('fi', 'Finnish'),
    ('sv', 'Swedish'),
]
TIME_ZONE = 'EET'
USE_I18N = True
USE_TZ = True
FORMAT_MODULE_PATH = 'aplus'
LOCALE_PATHS = (
    join(BASE_DIR, 'locale'),
)

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/ref/settings/#static-files
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'lib.storage.BumpStaticFilesStorage',
    },
}
STATICFILES_DIRS = (
    join(BASE_DIR, 'assets'),
)
STATIC_URL = '/static/'
STATIC_ROOT = join(BASE_DIR, 'static')

MEDIA_URL = '/media/'
MEDIA_ROOT = join(BASE_DIR, 'media')

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
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_VERSION': '2',
    'ALLOWED_VERSIONS': {
        # These are really just latest versions
        '1': '1.0',
        '2': '2.0',
    },
}


# Test environment url fixes. Typically not required for production.
REMOTE_PAGE_HOSTS_MAP = None

# Maximum submissions limit for exercises that allow unofficial submissions.
# The exercise-specific max submissions limit may then be exceeded, however,
# this limit will prevent students from spamming massive amounts of submissions.
# Set this value to zero in order to remove the limit.
MAX_UNOFFICIAL_SUBMISSIONS = 200

# Testing
# https://docs.djangoproject.com/en/1.7/topics/testing/advanced/
TEST_RUNNER = "xmlrunner.extra.djangotestrunner.XMLTestRunner"
TEST_OUTPUT_VERBOSE = True
TEST_OUTPUT_DESCRIPTIONS = True
TEST_OUTPUT_DIR = join(dirname(dirname(abspath(__file__))), "test_results")

# Logging
# https://docs.djangoproject.com/en/1.7/topics/logging/
LOGGING = {
  'version': 1,
  'disable_existing_loggers': False,
  'formatters': {
    'verbose': {
      'format': '[%(asctime)s: %(levelname)s/%(module)s] %(message)s'
    },
    'colored': {
      '()': 'r_django_essentials.logging.SourceColorizeFormatter',
      'format': '[%(asctime)s: %(levelname)s/%(module)s] %(message)s',
      'colors': {
        'django.db.backends': {'fg': 'cyan'},
        'django.db.deferred': {'fg': 'yellow'},
        'aplus': {'fg': 'blue'},
        'aplus.cached': {'fg': 'red'},
        'aplus.shibboleth': {'fg': 'red'},
      },
    },
  },
  'filters': {
    'skip_unreadable_post': {
        '()': 'django.utils.log.CallbackFilter',
        'callback': skip_unreadable_post,
    },
    'require_debug_true': {
      '()': 'django.utils.log.RequireDebugTrue',
    },
    'require_debug_false': {
      '()': 'django.utils.log.RequireDebugFalse',
    },
  },
  'handlers': {
    'debug_console': {
      'level': 'DEBUG',
      'filters': ['require_debug_true'],
      'class': 'logging.StreamHandler',
      'stream': 'ext://sys.stdout',
      'formatter': 'colored',
    },
    'console': {
      'level': 'DEBUG',
      'class': 'logging.StreamHandler',
      'stream': 'ext://sys.stdout',
      'formatter': 'verbose',
    },
    'email': {
      'level': 'ERROR',
      'filters': ['require_debug_false', 'skip_unreadable_post'],
      'class': 'django.utils.log.AdminEmailHandler',
    },
    'mail_admins': {
      # Duplicate of above, so if django internally refers it, we will use our filters
      'level': 'ERROR',
      'filters': ['require_debug_false', 'skip_unreadable_post'],
      'class': 'django.utils.log.AdminEmailHandler',
    },
  },
  'loggers': {
    '': {
      'level': 'INFO',
      'handlers': ['console', 'email'],
      'propagate': True
    },
    # Django defines these loggers internally, so we need to reconfigure them.
    'django': {
      'level': 'INFO',
      'handlers': ['console', 'email'],
    },
    'py.warnings': {
      'handlers': ['console'],
    },
  },
}


# We have a separate variable from DEBUG to enable the Django Debug Toolbar
# so that it is possible to enable and disable the toolbar regardless of
# the DEBUG value.
ENABLE_DJANGO_DEBUG_TOOLBAR = False



###############################################################################
#
# Logic to load settings from other files and tune them based on DEBUG
#

# Load settings from: local_settings, secret_key and environment
update_settings_with_file(__name__,
                          environ.get('APLUS_LOCAL_SETTINGS', 'local_settings'),
                          quiet='APLUS_LOCAL_SETTINGS' in environ)

# FIXME: deprecated. This was used with containers before, so keep it here for now.
update_settings_from_environment(__name__, 'DJANGO_')
# Load settings from environment variables starting with ENV_SETTINGS_PREFIX (default APLUS_)
ENV_SETTINGS_PREFIX = environ.get('ENV_SETTINGS_PREFIX', 'APLUS_')
update_settings_from_environment(__name__, ENV_SETTINGS_PREFIX)
update_secret_from_file(__name__, environ.get('APLUS_SECRET_KEY_FILE', 'secret_key'))

# Complain if BASE_URL is not set
try:
    if not BASE_URL:
        raise RuntimeError('Local setting BASE_URL can not be empty')
except NameError as e:
    raise RuntimeError('BASE_URL must be specified in local settings') from e

# update INSTALLED_APPS
if 'INSTALLED_LOGIN_APPS' in globals():
    INSTALLED_APPS = INSTALLED_LOGIN_APPS + INSTALLED_APPS # pylint: disable=undefined-variable

# update template loaders for production
use_cache_template_loader_in_production(__name__)

# setup authentication backends based on installed_apps
SOCIAL_AUTH = False
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
)
if 'shibboleth_login' in INSTALLED_APPS:
    AUTHENTICATION_BACKENDS += ('shibboleth_login.auth_backend.ShibbolethAuthBackend',)
if 'social_django' in INSTALLED_APPS:
    SOCIAL_AUTH = True
    AUTHENTICATION_BACKENDS += ('social_core.backends.google.GoogleOAuth2',)

APLUS_AUTH.update(APLUS_AUTH_LOCAL)



if DEBUG:
    # Allow basic auth for API when DEBUG is on
    REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] += ('rest_framework.authentication.BasicAuthentication',)
    # Enable defer logging
    from lib.models import install_defer_logger
    install_defer_logger()

if ENABLE_DJANGO_DEBUG_TOOLBAR:
    INSTALLED_APPS += ('debug_toolbar',)
    MIDDLEWARE.insert(
        0,
        'debug_toolbar.middleware.DebugToolbarMiddleware',
    )
    # The following variables may have been defined in local_settings.py or environment variables.
    try:
        if '127.0.0.1' not in INTERNAL_IPS: # pylint: disable=used-before-assignment
            INTERNAL_IPS.append('127.0.0.1')
    except NameError:
        INTERNAL_IPS = ['127.0.0.1']
    try:
        # pylint: disable-next=used-before-assignment
        DEBUG_TOOLBAR_CONFIG.setdefault('SHOW_TOOLBAR_CONFIG', 'lib.helpers.show_debug_toolbar')
    except NameError:
        DEBUG_TOOLBAR_CONFIG = {
            'SHOW_TOOLBAR_CALLBACK': 'lib.helpers.show_debug_toolbar',
        }
