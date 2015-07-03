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
    Retrieves the active external menu entries for a course instance.
    '''
    return MenuItem.objects.filter(
        course_instance__pk=course_instance_id,
        enabled=True,
        service__enabled=True,
    )
