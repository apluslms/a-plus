"""
Django settings for grader project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Note that this trick to find the base dir does not always work correctly.

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'y!*vae&k7l6#2^rjz#3_7@5v3!t^kvdvyhv1vdy*q_%dm%1p$q'
AJAX_KEY = 't76q54Gv'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [ "*" ]


# Application definition

INSTALLED_APPS = (
    # 'django.contrib.admin',
    # 'django.contrib.auth',
    # 'django.contrib.contenttypes',
    # 'django.contrib.sessions',
    # 'django.contrib.messages',
    'django.contrib.staticfiles',
    'access',
)
ADD_APPS = (
    #'gitmanager',
)

MIDDLEWARE_CLASSES = (
    # 'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    # 'django.contrib.auth.middleware.AuthenticationMiddleware',
    # 'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),
            os.path.join(BASE_DIR, 'courses'),
            os.path.join(BASE_DIR, 'exercises'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                #"django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Add project level static files
STATICFILES_DIRS = (os.path.join(BASE_DIR, 'static'),)

ROOT_URLCONF = 'grader.urls'

WSGI_APPLICATION = 'grader.wsgi.application'

# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True
LOCALE_PATHS = (os.path.join(BASE_DIR, 'locale'),)

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/
STATIC_URL = '/static/'
STATIC_URL_HOST_INJECT = ''

# HTTP
DEFAULT_EXPIRY_MINUTES = 15

#
# Task queue settings:
#
CONTAINER_MODE = False
CONTAINER_SCRIPT = os.path.join(BASE_DIR, "scripts/docker-run.sh")
CELERY_BROKER = False #'amqp://guest@localhost/'
RABBITMQ_MANAGEMENT = { "port": 55672, "password": "guest" }
CELERY_TASK_LIMIT_SEC = 2 * 60
CELERY_TASK_KILL_SEC = CELERY_TASK_LIMIT_SEC + 5
CELERY_AFFINITIES = []

#
# Task queue alert length via logging error.
#
QUEUE_ALERT_LENGTH = 20

#
# Sandbox process default limits.
# CELERY_TASK_LIMIT_SEC is enforced over this time limit.
#
SANDBOX_LIMITS = {
    "time": "-",
    "memory": "-",
    "files": "100",
    "disk": "1m",
}

#
# Exercise files submission path:
# Django process requires write access to this directory.
#
SUBMISSION_PATH = os.path.join(BASE_DIR, 'uploads')
#
# Personalized exercises and user files are kept here.
# Django process requires write access to this directory.
#
PERSONALIZED_CONTENT_PATH = os.path.join(BASE_DIR, 'exercises-meta')
#
# Enable personal directories for users, which can be used in personalized
# exercises to permanently store personal files with the
# grader.actions.store_user_files action. Personalized exercises can still be
# used even if this setting is False if the grading only uses the pregenerated
# exercise instance files. Enabling and using personal directories makes the
# grader stateful, which at least increases the amount of disk space used.
#
ENABLE_PERSONAL_DIRECTORIES = False

#
# Grading action scripts.
#
PREPARE_SCRIPT = os.path.join(BASE_DIR, "scripts/prepare.sh")
GITCLONE_SCRIPT = os.path.join(BASE_DIR, "scripts/gitclone.sh")
SANDBOX_RUNNER = os.path.join(BASE_DIR, "scripts/chroot_execvp")
SANDBOX_FALLBACK = os.path.join(BASE_DIR, "scripts/no_sandbox.sh")
EXPACA_SCRIPT = os.path.join(BASE_DIR, "scripts/expaca_grade.sh")
STORE_USER_FILES_SCRIPT = os.path.join(BASE_DIR, "scripts/store_user_files.sh")

#
# Define a dummy logging configuration:
#
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
      'level': 'DEBUG',
      'handlers': ['console']
    },
    'main': {
      'level': 'DEBUG',
      'handlers': ['email'],
      'propagate': True
    },
  },
}

#
# Import local settings overrides if any
#
try:
    from settings_local import *
except ImportError:
    pass

INSTALLED_APPS = INSTALLED_APPS + ADD_APPS
