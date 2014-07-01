'''
Tag usage:

{% load for_lti %}
{% for_lti course_instance.pk %}
<a href="{% url lti_login.views.lti_login url_key %}" target="_blank">
    {{ menu_label }}
</a>
{% endfor %}

''' 
from django import template
from lti_login.models import LTIMenuItem
from copy import copy

register = template.Library()


class ForLTINode(template.Node):
    '''
    Parsed For-LTI-node renders it's children nodes for each enabled menu item.
    
    '''
    def __init__(self, course_instance_pk, nodelist):
        self.course_instance_pk = template.Variable(course_instance_pk)
        self.nodelist = nodelist
    
    def render(self, context):
        out = ''
        try:
            pk = self.course_instance_pk.resolve(context)
            
            for_context = copy(context)
            for menu_item in LTIMenuItem.objects.filter(course_instance__pk=pk, enabled=True, service__enabled=True):
                
                for_context["url_key"] = menu_item.pk
                
                if menu_item.menu_label:
                    for_context["menu_label"] = menu_item.menu_label
                else:
                    for_context["menu_label"] = menu_item.service.menu_label

                if menu_item.menu_icon_class:
                    for_context["menu_icon_class"] = menu_item.menu_icon_class
                else:
                    for_context["menu_icon_class"] = menu_item.service.menu_icon_class
                
                out += self.nodelist.render(for_context)
        
        except template.VariableDoesNotExist:
            pass
        return out


@register.tag
def for_lti(parser, token):
    '''
    Parses for_lti tag in a template.
    Expects a course instance primary key as an argument.
    
    '''
    try:
        _, course_instance_pk = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError("%r tag requires a single argument" % token.contents.split()[0])
    
    # Collect all nodes until end token.
    nodelist = parser.parse(('endfor',))
    token = parser.next_token()
    assert token.contents == 'endfor'
    
    return ForLTINode(course_instance_pk, nodelist)
