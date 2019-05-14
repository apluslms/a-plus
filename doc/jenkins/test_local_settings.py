DEBUG = False

BRAND_NAME = 'A?'
SITEWIDE_ALERT_TEXT = '''<strong>Test version of A+</strong>: Real courses at
<a href="https://plus.cs.hut.fi/" class="alert-link">plus.cs.hut.fi</a>'''

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'aplus',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
        'TIMEOUT': None,
    }
}
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

#INSTALLED_LOGIN_APPS = (
#    'shibboleth_login',
#    'social.apps.django_app.default',
#)
#SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = ''
#SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = ''
