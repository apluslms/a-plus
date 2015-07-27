'''
Tag usage:

{% load external_services_tags %}
{% external_menu_entries course_instance.pk as entries %}
{% for entry in entries %}
<a href="{{ entry.url }}" target="_blank">
    {{ entry.label }}
</a>
{% endfor %}

'''
from django import template
from external_services.models import MenuItem


register = template.Library()


@register.assignment_tag
def external_menu_entries(course_instance_id):
    '''
    Retrieves the active student external menu entries for a course instance.
    '''
    return MenuItem.objects.filter(
        course_instance__pk=course_instance_id,
        enabled=True,
        service__enabled=True,
        access=MenuItem.ACCESS_STUDENT,
    )


@register.assignment_tag
def external_staff_menu_entries(course_instance_id, is_assistant, is_teacher):
    '''
    Retrieves the active student external staff menu entries.
    '''
    qs = MenuItem.objects.filter(
        course_instance__pk=course_instance_id,
        enabled=True,
        service__enabled=True,
        access__gt=MenuItem.ACCESS_STUDENT,
    )
    if is_teacher:
        return qs.exclude(access__gt=MenuItem.ACCESS_TEACHER)
    elif is_assistant:
        return qs.exclude(access__gt=MenuItem.ACCESS_ASSISTANT)
    return MenuItem.objects.none()
