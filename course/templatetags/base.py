from django import template
from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils.translation import get_language


register = template.Library()


@register.simple_tag
def brand_name():
    return mark_safe(settings.BRAND_NAME)


@register.simple_tag
def site_alert():
    message = settings.SITEWIDE_ALERT_TEXT
    if message:
        if isinstance(message, dict):
            message = message.get(get_language()) or message.get(settings.LANGUAGE_CODE[:2]) or message.values()[0]
        return mark_safe('<div class="alert alert-danger">{}</div>'.format(message))
    return ''


@register.simple_tag
def tracking_html():
    return mark_safe(settings.TRACKING_HTML)
