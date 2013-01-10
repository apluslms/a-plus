# Python
from datetime import datetime

# Django
from django import template
from django.template import Node
from django.template.loader import render_to_string

# A+
from course.models import CourseInstance, get_visible_open_course_instances

register = template.Library()

class CourseListNode(Node):
    def render(self, context):
        if context["user"] and context["user"].is_authenticated():
            visible_open_instances = get_visible_open_course_instances(
                context["user"].get_profile())
        else:
            visible_open_instances = get_visible_open_course_instances()
        
        return render_to_string('course/_course_dropdown_menu.html', {
            "instances": visible_open_instances})

@register.tag
def render_course_list(parser, token):
    return CourseListNode()
