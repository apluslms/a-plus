
from django import template
from notification.models import NotificationSet

register = template.Library()

@register.assignment_tag
def unread_notifications(user):
    return NotificationSet.get_unread(user)

@register.assignment_tag
def new_course_notifications(course_instance, user):
    return NotificationSet.get_course_unread_and_mark(course_instance, user)

@register.assignment_tag
def old_course_notifications(course_instance, user):
    return NotificationSet.get_course_read(course_instance, user)
