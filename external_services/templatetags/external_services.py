from django import template

from cached.menu import CachedCourseMenu
from lib.errors import TagUsageError
from ..models import MenuItem


register = template.Library()


@register.simple_tag(takes_context=True)
def prepare_course_menu(context):
    if not 'instance' in context:
        raise TagUsageError()
    if not 'course_menu' in context:
        context['course_menu'] = CachedCourseMenu(context['instance'])
    return ""


@register.filter
def is_assistant_link(entry):
    return CachedCourseMenu.is_assistant_link(entry['access'])
