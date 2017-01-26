from django import template
from django.conf import settings


register = template.Library()


@register.simple_tag
def brand_name():
    return settings.BRAND_NAME


@register.simple_tag
def site_alert():
    if settings.SITEWIDE_ALERT_TEXT:
        return '<div class="alert alert-danger">{}</div>'.format(
            settings.SITEWIDE_ALERT_TEXT)
    return ''


@register.simple_tag
def tracking_html():
    return settings.TRACKING_HTML
