# Default settings for a-plus Django project.
# You should create local_settings.py in the same directory to override necessary settings
import os, sys

# Lines for Celery. Disabled until actually needed
# import djcelery
# djcelery.setup_loader()

# Returns the path to given filename
def get_path(filename):
    return os.path.join(os.path.dirname(__file__), filename)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ALLOWED_HOSTS = []

# This URL is used when building absolute URLs to this service
# Must be overridden in local_settings.py for deployment
BASE_URL = "http://localhost:8000"

# Make this unique, and don't share it with anybody.
# Must be overridden in local_settings.py for deployment
SECRET_KEY = '&lr5&01mgf9+=!7%rz1&0pfff&oy_uy(8%c8&l+c(kxt&=u87d'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': get_path('aplus.db'),            # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Helsinki'
# Datetimes will be unaware of timezone
USE_TZ = False

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# TODO: Should this be used?
# USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = get_path("media/")

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = get_path("static/")

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    get_path('assets'),
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.load_template_source',
)

# Cache backends
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'django_db_cache',
    }
}

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'userprofile.middleware.StudentGroupMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'lib.middleware.SqlInjectionMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.contrib.messages.context_processors.messages",
    "userprofile.context_processors.student_group",
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    get_path('templates'),
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    # Django applications
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.auth',

    # Third party applications
    'django_shibboleth', #for shibboleth logins
    'tastypie_oauth',
    'oauth_provider',
    'oauth2_provider',

    # First party applications
    'external_services',
    'notification',
    'inheritance',
    'userprofile',
    'exercise',
    'course',
    'oembed',
    'apps',
)

TEST_EXCLUDE_APPS = (
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.auth',

    'django_shibboleth',
    'tastypie_oauth',
    'oauth_provider',
    'oauth2_provider',
    'south',
)

# OAuth settings
OAUTH_AUTHORIZE_VIEW = 'oauth_provider.custom_views.oauth_authorize'
OAUTH_ACCESS_TOKEN_MODEL = 'oauth2_provider.models.AccessToken'
LOGIN_REDIRECT_URL = "/"

AUTH_PROFILE_MODULE = 'userprofile.UserProfile'

FILE_UPLOAD_HANDLERS = (
    #"django.core.files.uploadhandler.MemoryFileUploadHandler",
    "django.core.files.uploadhandler.TemporaryFileUploadHandler",
)


# Shibboleth settings
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


#TODO fix with python3
# Unit test XML-reporting
TEST_RUNNER = 'django.test.runner.DiscoverRunner'
# TEST_RUNNER = "test_runner.custom_xml_test_runner.ExcludeAppsXMLTestRunner"
# TEST_OUTPUT_VERBOSE = True
# TEST_OUTPUT_DESCRIPTIONS = True
# TEST_OUTPUT_DIR = "test_results"

# Overrides and appends settings defined in local_settings.py
try:
    from local_settings import *
except ImportError:
    pass
