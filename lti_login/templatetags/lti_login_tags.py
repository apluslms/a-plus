'''
Tag usage:

{% load lti_login_tags %}
{% lti_login_entries course_instance.pk %}
{% for entry in lti_menu_entries %}
<a href="{% url lti_login.views.lti_login entry.id %}" target="_blank">
    {{ entry.label }}
</a>
{% endfor %}

''' 
from django import template
from lti_login.models import LTIMenuItem

register = template.Library()

@register.simple_tag(takes_context=True)
def lti_login_entries(context, course_instance_id):
    '''
    Retrieves the active LTI menu entries for a course instance.
    
    @type course_instance_id: C{str}
    @param course_instance_id: a course instance primary key
    @rtype: C{str}
    @return: empty string 
    '''
    context["lti_menu_entries"] = LTIMenuItem.objects.filter(
        course_instance__pk=course_instance_id,
        enabled=True,
        service__enabled=True)
    return ""
