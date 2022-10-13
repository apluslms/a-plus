import logging

from django.conf import settings
from django.contrib.auth import (
    REDIRECT_FIELD_NAME,
    authenticate,
    login as django_login,
)
from django.http import HttpResponseRedirect
from django.http.response import HttpResponse
from django.shortcuts import render, resolve_url
from django.utils.http import is_safe_url
from django.utils.translation import gettext_lazy as _

from .apps import env_settings
from .parser import Parser


logger = logging.getLogger('aplus.shibboleth')


class ShibbolethException(Exception):
    """
    Signals problems processing Shibboleth request.

    """
    def __init__(self, message):
        self.message = message
        super().__init__()


def _filter_environment(env, prefix):
    prefix = prefix.upper()
    prefix_len = len(prefix)
    env = ((k.upper(), v) for k, v in env.items())
    return {
        name[prefix_len:]: value
        for name, value in env
        if name.startswith(prefix)
    }


def login(request):
    try:
        env = _filter_environment(request.META, env_settings.PREFIX)
        user = authenticate(request=request, shibd_meta=env)
        if not user:
            raise ShibbolethException(
                _('SHIBBOLETH_ERROR_LOGIN_FAILED_META_HEADERS_MISSING')
            )
        if not user.is_active:
            # pylint: disable-next=logging-format-interpolation
            logger.warning("Shibboleth login attempt for inactive user: {}".format(user.username))
            raise ShibbolethException(
                _('SHIBBOLETH_ERROR_USER_ACCOUNT_DISABLED')
            )

        django_login(request, user)
        logger.debug("Shibboleth login: {}".format(user.username)) # pylint: disable=logging-format-interpolation

        redirect_to = request.GET.get(REDIRECT_FIELD_NAME, '')
        if not is_safe_url(url=redirect_to,
                           allowed_hosts={request.get_host()},
                           require_https=request.is_secure(),
                           ):
            redirect_to = resolve_url(settings.LOGIN_REDIRECT_URL)

        return HttpResponseRedirect(redirect_to)

    except ShibbolethException as e:
        return HttpResponse(e.message, content_type='text/plain', status=403)


def _safe_hyphens(s):
    from django.utils.safestring import mark_safe # pylint: disable=import-outside-toplevel
    from django.utils.html import escape # pylint: disable=import-outside-toplevel
    s = '&#8209;'.join(escape(x) for x in s.split('-'))
    return mark_safe(s)


def debug(request):
    shib_prefix = env_settings.PREFIX
    parser = Parser(env=request.META,
                    urldecode=env_settings.URL_DECODE)

    shib_meta = []
    headers = []
    meta = []
    for k, v in request.META.items():
        if '.' in k:
            continue
        if k.startswith(shib_prefix):
            shib_meta.append((k, parser.get_values(k)))
        elif k.startswith('HTTP_'):
            headers.append((_safe_hyphens(k[5:].lower().replace('_', '-')), v))
        meta.append((k, v))

    shib_meta.sort()
    headers.sort()
    meta.sort()

    return render(request, 'shibboleth/meta.html',
        {'shib_meta': shib_meta, 'headers': headers, 'meta': meta})
