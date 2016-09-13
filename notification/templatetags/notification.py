
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


def _context_unread(context):
    if not "unread" in context:
        user = _context_user(context)
        context["unread"] = NotificationSet.get_unread(user)
    return context["unread"]


def _unread_messages(context):
    unread = _context_unread(context)
    return {
        "unread": unread,
        "unread_message": ungettext(
            "new notification",
            "new notifications",
            unread.count
        ),
    }


@register.inclusion_tag("notification/_notification_messages.html", takes_context=True)
def notification_messages(context):
    return _unread_messages(context)


@register.inclusion_tag("notification/_notification_menu.html", takes_context=True)
def notification_menu(context):
    return _unread_messages(context)


@register.assignment_tag(takes_context=True)
def notification_count(context):
    unread = _context_unread(context)
    return unread.count
