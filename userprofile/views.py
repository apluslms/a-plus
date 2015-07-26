from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import login as django_login
from django.http.response import HttpResponseRedirect
from django.shortcuts import resolve_url
from django.utils.http import is_safe_url


def login(request):
    """
    Wraps the default login view in Django. Additionally redirects already
    authenticated users automatically to the target.
    """
    if request.user.is_authenticated():
        redirect_to = request.POST.get(REDIRECT_FIELD_NAME,
                                       request.GET.get(REDIRECT_FIELD_NAME, ''))
        if not is_safe_url(url=redirect_to, host=request.get_host()):
            redirect_to = resolve_url(settings.LOGIN_REDIRECT_URL)
        return HttpResponseRedirect(redirect_to)

    return django_login(
        request,
        template_name="userprofile/login.html",
        extra_context={
            'shibboleth_login': 'shibboleth_login' in settings.INSTALLED_APPS,
            'login_title_text': settings.LOGIN_TITLE_TEXT,
            'login_body_text': settings.LOGIN_BODY_TEXT,
            'login_button_text': settings.LOGIN_BUTTON_TEXT,
        }
    )
