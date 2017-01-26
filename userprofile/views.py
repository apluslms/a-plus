from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import login as django_login
from django.http.response import HttpResponseRedirect
from django.shortcuts import resolve_url
from django.utils.http import is_safe_url

from lib.helpers import settings_text
from authorization.permissions import ACCESS
from .viewbase import UserProfileView


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
            'mooc_login': 'social.apps.django_app.default' in settings.INSTALLED_APPS,
            'login_title_text': settings_text('LOGIN_TITLE_TEXT'),
            'login_body_text': settings_text('LOGIN_BODY_TEXT'),
            'login_button_text': settings_text('LOGIN_BUTTON_TEXT'),
            'shibboleth_title_text': settings_text('SHIBBOLETH_TITLE_TEXT'),
            'shibboleth_body_text': settings_text('SHIBBOLETH_BODY_TEXT'),
            'shibboleth_button_text': settings_text('SHIBBOLETH_BUTTON_TEXT'),
            'mooc_title_text': settings_text('MOOC_TITLE_TEXT'),
            'mooc_body_text': settings_text('MOOC_BODY_TEXT'),
        }
    )


class PrivacyPolicyView(UserProfileView):
    access_mode=ACCESS.ANONYMOUS
    template_name="userprofile/privacy.html"

    def get_common_objects(self):
        super().get_common_objects()
        self.policy_text = settings_text('PRIVACY_POLICY_TEXT')
        self.note("policy_text")
