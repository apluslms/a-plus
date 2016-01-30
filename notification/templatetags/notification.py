
from django import template
from django.utils.translation import ungettext
from notification.models import NotificationSet

register = template.Library()


def _context_user(context):
    if "request" in context:
        user = context["request"].user
        if user.is_authenticated():
            return user
    return None


def _unread_messages(context):
    unread = []
    message = ""
    user = _context_user(context)
    if user:
        unread = NotificationSet.get_unread(user)
        message = ungettext(
            'new notification',
            'new notifications',
            unread.count
        )
    return {
        "unread": unread,
        "unread_message": message,
    }


@register.inclusion_tag("notification/_notification_messages.html", takes_context=True)
def notification_messages(context):
    return _unread_messages(context)


@register.inclusion_tag("notification/_notification_menu.html", takes_context=True)
def notification_menu(context):
    return _unread_messages(context)


@register.assignment_tag(takes_context=True)
def notification_count(context):
    user = _context_user(context)
    if user and "instance" in context:
        return NotificationSet.get_course_new_count(context["instance"], user)
    return 0
