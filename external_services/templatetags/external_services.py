import string
from django import template

from lib.errors import TagUsageError
from lib.helpers import get_random_string
from ..cache import CachedCourseMenu
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
    return CachedCourseMenu.is_assistant_link(entry)


@register.filter
def menu_access(access):
    return MenuItem.ACCESS[access]


@register.simple_tag
def random_id(length=11):
    # start HTML ids with an alphabet, not a digit
    return 'r' + get_random_string(length - 1, choices=string.ascii_lowercase + string.digits)
