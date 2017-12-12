from django import template
from django.conf import settings
from django.utils.safestring import mark_safe


register = template.Library()


@register.simple_tag
def brand_name():
    return mark_safe(settings.BRAND_NAME)


@register.simple_tag
def site_alert():
    if settings.SITEWIDE_ALERT_TEXT:
        return mark_safe(
            '<div class="alert alert-danger">{}</div>'.format(
                settings.SITEWIDE_ALERT_TEXT)
            )
    return ''


@register.simple_tag
def tracking_html():
    return mark_safe(settings.TRACKING_HTML)
