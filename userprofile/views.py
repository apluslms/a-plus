import logging
from urllib.parse import unquote

from django.conf import settings
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.http import HttpResponse, HttpResponseRedirect
from django.template.loader import TemplateDoesNotExist, get_template
from django.urls import translate_url
from django.utils.http import is_safe_url
from django.utils.translation import (
    LANGUAGE_SESSION_KEY,
    check_for_language,
    get_language
)
from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext

from lib.helpers import settings_text, remove_query_param_from_url
from authorization.permissions import ACCESS
from .viewbase import UserProfileView


logger = logging.getLogger('aplus.userprofile')


class CustomLoginView(LoginView):
    """This login view class extends the default Django login class and
    overrides some of the default settings. Namely, the template and its context."""

    template_name = "userprofile/login.html"
    redirect_authenticated_user = True
    # Redirecting authenticated users enables "social media fingerprinting"
    # unless images are hosted on a different domain from the Django app.
    extra_context = {
        'shibboleth_login': 'shibboleth_login' in settings.INSTALLED_APPS,
        'mooc_login': 'social_django' in settings.INSTALLED_APPS,
        'brand_name': settings_text('BRAND_NAME'),
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # The following template context parameters can not be defined in
        # the class variable extra_context because they require that Django
        # translations are active. That is, there must be an HTTP request so
        # that the language can be defined. There is no request in the code
        # in the class level, but there is a request when this method is called
        # (self.request).
        context.update({
            'shibboleth_title_text': settings_text('SHIBBOLETH_TITLE_TEXT'),
            'shibboleth_body_text': settings_text('SHIBBOLETH_BODY_TEXT'),
            'shibboleth_button_text': settings_text('SHIBBOLETH_BUTTON_TEXT'),
            'mooc_title_text': settings_text('MOOC_TITLE_TEXT'),
            'mooc_body_text': settings_text('MOOC_BODY_TEXT'),
        })
        return context


def set_user_language(request):
    """"Overrides set_language function from  django.views.i18n."""
    LANGUAGE_PARAMETER = 'language'

    next = remove_query_param_from_url(request.POST.get('next', request.GET.get('next')), 'hl')
    if ((next or not request.is_ajax()) and
            not is_safe_url(url=next,
                            allowed_hosts={request.get_host()},
                            require_https=request.is_secure())):
        next = remove_query_param_from_url(request.META.get('HTTP_REFERER'), 'hl')
        next = next and unquote(next)  # HTTP_REFERER may be encoded.
        if not is_safe_url(url=next,
                            allowed_hosts={request.get_host()},
                            require_https=request.is_secure()):
            next = '/'
    response = HttpResponseRedirect(next) if next else HttpResponse(status=204)
    if request.method == 'POST':
        lang_code = request.POST.get(LANGUAGE_PARAMETER)
        if lang_code and check_for_language(lang_code):
            if next:
                next_trans = translate_url(next, lang_code)
                if next_trans != next:
                    response = HttpResponseRedirect(next_trans)
            if request.user.is_authenticated:
                userprofile = request.user.userprofile
                userprofile.language = lang_code
                userprofile.save()
            else:
                if hasattr(request, 'session'):
                    request.session[LANGUAGE_SESSION_KEY] = lang_code
                response.set_cookie(
                    settings.LANGUAGE_COOKIE_NAME, lang_code,
                    max_age=settings.LANGUAGE_COOKIE_AGE,
                    path=settings.LANGUAGE_COOKIE_PATH,
                    domain=settings.LANGUAGE_COOKIE_DOMAIN,
                )
    return response


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


class AccessibilityStatementView(UserProfileView):
    access_mode = ACCESS.ANONYMOUS
    template_name="userprofile/accessibility.html"

    def get_common_objects(self):
        super().get_common_objects()
        lang = "_" + get_language().lower()
        key = make_template_fragment_key('accessibility_statement', [lang])
        accessibility_statement = cache.get(key)
        # TODO: refactor to a helper function
        if not accessibility_statement:
            local_template_name = "institution_accessibility_text{}.html"
            local_template = try_get_template(local_template_name.format(lang))
            if not local_template and len(lang) > 3:
                local_template = try_get_template(local_template_name.format(lang[:3]))
            if not local_template:
                logger.warning("No localized accessibility statement for language %s", lang)
                local_template = try_get_template(local_template_name.format(''))
            if not local_template:
                logger.error("No local accessibility content at all!")

            local_accessibility_statement = local_template.render() if local_template else gettext("No local accessibility statement. Please notify the site's owner!")

            system_template_name = "accessibility_issues{}.html"
            system_template = try_get_template(system_template_name.format(lang))
            if not system_template and len(lang) > 3:
                system_template = try_get_template(system_template_name.format(lang[:3]))
            if not system_template:
                logger.warning("No localized system accessibility content for language %s", lang)
                system_template = try_get_template(system_template_name.format(''))
            if not system_template:
                logger.error("No system accessibility content at all!")

            system_accessibility_statement = system_template.render() if system_template else gettext("No system-wide accessibility statement found.")

            accessibility_statement = local_accessibility_statement + system_accessibility_statement
            cache.set(key, accessibility_statement)
        self.accessibility_statement = accessibility_statement
        self.note("accessibility_statement")

class SupportView(UserProfileView):
    access_mode = ACCESS.ANONYMOUS
    template_name = "userprofile/support.html"
    extra_context = {
        'brand_name': settings_text('BRAND_NAME'),
        'brand_name_long': settings_text('BRAND_NAME_LONG'),
        'brand_institution_name': settings_text('BRAND_INSTITUTION_NAME'),
    }

    def get_common_objects(self):
        super().get_common_objects()
        lang = "_" + get_language().lower()
        key = make_template_fragment_key('support_channels', [lang])
        support_channels = cache.get(key)

        if not support_channels:
            template_name = "support_channels{}.html"
            template = try_get_template(template_name.format(lang))

            if not template and len(lang) > 3:
                template = try_get_template(template_name.format(lang[:3]))
            if not template:
                template = try_get_template(template_name.format(''))
            if not template:
                logger.error("The support page is missing")

            support_channels = template.render() if template else _("No support page. Please notify administration!")

            cache.set(key, support_channels)

        self.support_channels = support_channels
        self.note("support_channels")

class ProfileView(UserProfileView):
    template_name = "userprofile/profile.html"
    extra_context = {
        'brand_name': settings_text('BRAND_NAME'),
    }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_google'] = (
            self.request.user.social_auth.filter(provider="google-oauth2").exists()
            if settings.SOCIAL_AUTH
            else False
        )

        return context
