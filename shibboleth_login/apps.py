import re

from django.apps import AppConfig
from django_settingsdict import SettingsDict


class AplusShibbolethLoginConfig(AppConfig):
    name = 'shibboleth_login'
    verbose_name = 'A+ Shibboleth Login'


def _only_prefix(value, env): # pylint: disable=unused-argument
    return re.sub(r'^((?:HTTP_)?[^_-]+[_-]).*$', r'\1', value)


def _drop_prefix(value, env):
    prefix = env.get('PREFIX', '')
    if value.startswith(prefix):
        return value[len(prefix):]
    return value


app_settings = SettingsDict(
    'SHIBBOLETH_LOGIN',
    defaults={
        'ALLOW_CREATE_NEW_USERS': True,
        'ALLOW_SEARCH_WITH_EMAIL': False,
    },
)


env_settings = SettingsDict(
    'SHIBBOLETH_ENVIRONMENT_VARS',
    required=[
        # This is typically SHIB_ for Apache 2 and
        # HTTP_SHIB_ for nginx with http roxy
        'PREFIX',
        # Domain where student numbers are valid
        # NOTE: this is temporary, until A+ supports multiple domains
        'STUDENT_DOMAIN',
    ],
    defaults={
        'USER_ID': 'eppn',
        'FIRST_NAME': 'givenName',
        'LAST_NAME': 'sn',
        'COMMON_NAME': 'cn',
        'FULL_NAME': 'displayName',
        'EMAIL': 'mail',
        'LANGUAGE': 'preferredLanguage',
        # student values are based on Haka Federation
        # https://wiki.eduuni.fi/display/CSCHAKA/Federation
        'STUDENT_IDS': 'schacPersonalUniqueCode',
        'STUDENT_URN': ':schac:personalUniqueCode:',
        'HOME_ORGANIZATION': 'schacHomeOrganization',
        'STUDENT_FILTERS': {
            2: 'studentID',
            3: 'int',
        },
        'URL_DECODE': True,
    },
    migrate=[
        # new name, old name, migration script
        ('PREFIX', 'SHIB_USER_ID_KEY', _only_prefix),
        ('USER_ID', 'SHIB_USER_ID_KEY', _drop_prefix),
        ('FIRST_NAME', 'SHIB_FIRST_NAME_KEY', _drop_prefix),
        ('LAST_NAME', 'SHIB_LAST_NAME_KEY', _drop_prefix),
        ('EMAIL', 'SHIB_MAIL_KEY', _drop_prefix),
        ('STUDENT_IDS', 'SHIB_STUDENT_ID_KEY', _drop_prefix),
        ('URL_DECODE', 'SHIBBOLETH_VARIABLES_URL_ENCODED'),
    ],
)
