from django import template
from django.conf import settings

from course.models import CourseInstance


register = template.Library()


@register.inclusion_tag("course/_course_dropdown_menu.html", takes_context=True)
def course_menu(context):
    return { "instances": CourseInstance.objects.get_active(context["user"]) }


@register.filter
def url(model_object, name=None):
    if name:
        return model_object.get_url(name)
    return model_object.get_absolute_url()


@register.simple_tag
def brand_name():
    return settings.BRAND_NAME


@register.simple_tag
def site_alert():
    if settings.SITEWIDE_ALERT_TEXT:
        return '<div class="alert alert-danger">{}</div>'.format(
            settings.SITEWIDE_ALERT_TEXT)
    return ''
