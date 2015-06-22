
from django import template
from django.template import Node
from django.template.loader import render_to_string

from course.models import CourseInstance


register = template.Library()

class CourseListNode(Node):
    
    def render(self, context):
        return render_to_string('course/_course_dropdown_menu.html', {
            "instances": CourseInstance.objects.get_active(context["user"]) })

@register.tag
def render_course_list(parser, token):
    return CourseListNode()


@register.filter
def course_module_classes(course_module):
    """
    Returns the CSS classes for the course module.
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

@register.filter
def exercise_summary_classes(exercise_summary):
    classes = []
    if not exercise_summary.is_passed():
        classes.append("btn-danger")
    elif exercise_summary.is_submitted():
        if exercise_summary.is_full_points():
            classes.append("btn-success")
        else:
            classes.append("btn-warning")
    return " ".join(classes)
