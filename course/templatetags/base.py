from datetime import datetime

from django import template
from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils.translation import get_language, gettext_lazy as _
from lib.helpers import remove_query_param_from_url, settings_text, update_url_params
from exercise.submission_models import PendingSubmission


register = template.Library()


def pick_localized(message):
    if message and isinstance(message, dict):
        return (message.get(get_language()) or
                message.get(settings.LANGUAGE_CODE[:2]) or
                message.values()[0])
    return message


def get_date(cont, key):
    data = cont.get(key)
    if data and not isinstance(data, datetime):
        data = datetime.strptime(data, '%Y-%m-%d')
        cont[key] = data
    return data


@register.simple_tag
def brand_name():
    return mark_safe(settings.BRAND_NAME)

@register.simple_tag
def brand_name_long():
    return mark_safe(settings.BRAND_NAME_LONG)

@register.simple_tag
def brand_institution_name():
    return mark_safe(settings_text('BRAND_INSTITUTION_NAME'))

@register.simple_tag
def site_alert():
    message = settings.SITEWIDE_ALERT_TEXT
    if message:
        return mark_safe('<div class="alert alert-danger">{}</div>'
                         .format(pick_localized(message)))
    if not PendingSubmission.objects.is_grader_stable():
        # Prefer configured alert text, if one is set
        return mark_safe('<div class="alert alert-danger">{}</div>'.format(_('GRADER_PROBLEMS_ALERT')))
    return ''


@register.simple_tag
def site_advert():
    advert = settings.SITEWIDE_ADVERT
    if not advert or not isinstance(advert, dict):
        return
    not_before = get_date(advert, 'not-before')
    not_after = get_date(advert, 'not-after')
    if not_before or not_after:
        now = datetime.now()
        if not_before and not_before > now:
            return
        if not_after and not_after < now:
            return
    return {k: pick_localized(advert.get(k))
            for k in ('title', 'text', 'href', 'image')}


@register.simple_tag
def tracking_html():
    return mark_safe(settings.TRACKING_HTML)


@register.filter
def localized_url(path, language=None):
    base_url = settings.BASE_URL
    if base_url.endswith('/'):
        base_url = base_url[:-1]
    path = remove_query_param_from_url(path, 'hl')
    if not language:
        language = settings.LANGUAGE_CODE.split('-')[0]
    path = update_url_params(path, { 'hl': language })
    return base_url + path
