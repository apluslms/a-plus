
from django import template
from notification.models import NotificationSet

register = template.Library()


@register.inclusion_tag("notification/_notification_messages.html", takes_context=True)
def notification_messages(context):
    unread = []
    if "request" in context:
        user = context["request"].user
        if user.is_authenticated():
            unread = NotificationSet.get_unread(user)
    return {
        "unread": unread,
    }

@register.assignment_tag
def new_course_notifications(course_instance, user):
    return NotificationSet.get_course_unread_and_mark(course_instance, user)


@register.assignment_tag
def old_course_notifications(course_instance, user):
    return NotificationSet.get_course_read(course_instance, user)
