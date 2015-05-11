'''
Tag usage:

{% load external_services_tags %}
{% ext_service_entries course_instance.pk %}
{% for entry in ext_menu_entries %}
<a href="{{ entry.url }}" target="_blank">
    {{ entry.label }}
</a>
{% endfor %}

'''
from django import template
from external_services.models import MenuItem

register = template.Library()

@register.simple_tag(takes_context=True)
def ext_service_entries(context, course_instance_id):
    '''
    Retrieves the active external menu entries for a course instance
    and adds them to the context variable.

    @type course_instance_id: C{str}
    @param course_instance_id: a course instance primary key
    @rtype: C{str}
    @return: empty string
    '''
    context["ext_menu_entries"] = MenuItem.objects.filter(
        course_instance__pk=course_instance_id,
        enabled=True,
        service__enabled=True)
    return ""
