import logging

from urllib.parse import unquote

from django.conf import settings
from django.contrib.auth import login as django_login, authenticate, \
    REDIRECT_FIELD_NAME
from django.http import HttpResponseRedirect
from django.http.response import HttpResponse
from django.shortcuts import render, resolve_url
from django.utils.http import is_safe_url
from django.utils.translation import ugettext_lazy as _


logger = logging.getLogger('aplus.shibboleth')


class ShibbolethException(Exception):
    """
    Signals problems processing Shibboleth request.
    
    """
    def __init__(self, message):
        self.message = message
        super(ShibbolethException, self).__init__()


def login(request):
    try:
        user = authenticate(request=request, shibd_meta=request.META)
        if not user:
            raise ShibbolethException(
                _("Failed to login the user. "
                  "Shibboleth META headers missing. "
                  "Check the Apache mod_shibd is active and /shibboleth is protected.")
            )
        if not user.is_active:
            logger.warning("Shibboleth login attempt for inactive user: {}".format(user.username))
            raise ShibbolethException(
                _("The user account has been disabled.")
            )

        django_login(request, user)
        logger.debug("Shibboleth login: {}".format(user.username))
        
        redirect_to = request.GET.get(REDIRECT_FIELD_NAME, '')
        if not is_safe_url(url=redirect_to, allowed_hosts={request.get_host()}):
            redirect_to = resolve_url(settings.LOGIN_REDIRECT_URL)
        
        return HttpResponseRedirect(redirect_to)
    
    except ShibbolethException as e:
        return HttpResponse(e.message, content_type='text/plain', status=403)


def debug(request):
    meta = [
        (k.replace('-', '_').upper(), v)
        for k, v in request.META.items()
        if '.' not in k
    ]
    if settings.SHIBBOLETH_VARIABLES_URL_ENCODED:
        # FIXME: shibboleth variables might not start with SHIB, use settings values here
        meta = [
            (k, (unquote(v) if k.startswith('SHIB') else v))
            for k, v in meta
        ]
    meta.sort()
    return render(request, 'shibboleth/meta.html', {'meta_data': meta})
