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
                context["user"].userprofile)
        else:
            visible_open_instances = get_visible_open_course_instances()

        return render_to_string('course/_course_dropdown_menu.html', {
            "instances": visible_open_instances})

@register.tag
def render_course_list(parser, token):
    return CourseListNode()

@register.filter
def course_module_classes(course_module):
    """
    Returns the CSS classes that should be used for this course_module in the
    view_instance view.
    """
    classes = []
    if course_module.is_open():
        classes.append("open")
    elif course_module.is_after_open():
        classes.append("closed")
        classes.append("collapsed")
    else:
        classes.append("upcoming")
        classes.append("collapsed")

    return " ".join(classes)
