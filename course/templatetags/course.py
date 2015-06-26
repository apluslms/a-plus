
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
def course_menu(parser, token):
    return CourseListNode()
