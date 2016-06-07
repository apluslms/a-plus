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

# Add project level templates and static files
TEMPLATE_DIRS = (os.path.join(BASE_DIR, 'templates'), os.path.join(BASE_DIR, 'exercises'))
STATICFILES_DIRS = (os.path.join(BASE_DIR, 'static'),)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'y!*vae&k7l6#2^rjz#3_7@5v3!t^kvdvyhv1vdy*q_%dm%1p$q'
AJAX_KEY = 't76q54Gv'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

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

TEMPLATE_CONTEXT_PROCESSORS = (
    #"django.contrib.auth.context_processors.auth",
    "django.template.context_processors.debug",
    "django.template.context_processors.i18n",
    "django.template.context_processors.media",
    "django.template.context_processors.static",
    "django.template.context_processors.tz",
    "django.contrib.messages.context_processors.messages",
)

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

#
# Celery task queue settings:
#
CELERY_BROKER = False
#CELERY_BROKER = 'amqp://guest@localhost/'
RABBITMQ_MANAGEMENT = { "port": 55672, "password": "guest" }
CELERY_TASK_LIMIT_SEC = 2 * 60
CELERY_TASK_KILL_SEC = CELERY_TASK_LIMIT_SEC + 5

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
# Grading action scripts.
#
PREPARE_SCRIPT = os.path.join(BASE_DIR, "scripts/prepare.sh")
GITCLONE_SCRIPT = os.path.join(BASE_DIR, "scripts/gitclone.sh")
SANDBOX_RUNNER = os.path.join(BASE_DIR, "scripts/chroot_execvp")
SANDBOX_FALLBACK = os.path.join(BASE_DIR, "scripts/no_sandbox.sh")
EXPACA_SCRIPT = os.path.join(BASE_DIR, "scripts/expaca_grade.sh")

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
