import logging
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import login as django_login
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.http.response import HttpResponseRedirect
from django.shortcuts import resolve_url
from django.template.loader import TemplateDoesNotExist, get_template
from django.utils.http import is_safe_url
from django.utils.translation import get_language
from django.utils.translation import ugettext_lazy as _

from lib.helpers import settings_text
from authorization.permissions import ACCESS
from .viewbase import UserProfileView


logger = logging.getLogger('userprofile.views')


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
            'mooc_login': 'social_django' in settings.INSTALLED_APPS,
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


def try_get_template(name):
    try:
        return get_template(name)
    except TemplateDoesNotExist:
        logger.info("Template %s not found", name)
        return None


class PrivacyNoticeView(UserProfileView):
    access_mode=ACCESS.ANONYMOUS
    template_name="userprofile/privacy.html"

    def get_common_objects(self):
        super().get_common_objects()
        lang = "_" + get_language().lower()
        key = make_template_fragment_key('privacy_notice', [lang])
        privacy_text = cache.get(key)
        if not privacy_text:
            template_name = "privacy_notice{}.html"
            template = try_get_template(template_name.format(lang))
            if not template and len(lang) > 3:
                template = try_get_template(template_name.format(lang[:3]))
            if not template:
                logger.warning("No localized privacy notice for language %s", lang)
                template = try_get_template(template_name.format(''))
            if not template:
                logger.error("No privacy notice at all!")

            privacy_text = template.render() if template else _("No privacy notice. Please notify administration!")
            cache.set(key, privacy_text)
        self.privacy_text = privacy_text
        self.note("privacy_text")

class ProfileView(UserProfileView):
    template_name = "userprofile/profile.html"
