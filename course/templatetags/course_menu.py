# Python
from datetime import datetime

# Django
from django import template
from django.template import Node
from django.template.loader import render_to_string

# A+
from course.models import CourseInstance

register = template.Library()

class CourseListNode(Node):
    def render(self, context):
        open_instances = CourseInstance.objects.filter(ending_time__gt=datetime.now())
        return render_to_string('course/_course_dropdown_menu.html', {"instances": open_instances})

@register.tag
def render_course_list(parser, token):
    return CourseListNode()
