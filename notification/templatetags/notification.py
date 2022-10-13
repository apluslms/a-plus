from django import template
from django.utils.translation import ngettext

from ..cache import CachedNotifications


register = template.Library()


def _context_unread(context):
    if 'notifications' not in context:
        context['notifications'] = CachedNotifications(
            context['request'].user if 'request' in context else None
        )
    return context['notifications']


def _unread_messages(context):
    notifications = _context_unread(context)
    return {
        'count': notifications.count(),
        'notifications': notifications.notifications(),
        "unread_message": ngettext(
            'NEW_NOTIFICATION',
            'NEW_NOTIFICATIONS',
            notifications.count()
        ),
    }


@register.inclusion_tag("notification/_notification_messages.html", takes_context=True)
def notification_messages(context):
    return _unread_messages(context)


@register.inclusion_tag("notification/_notification_menu.html", takes_context=True)
def notification_menu(context):
    return _unread_messages(context)


@register.simple_tag(takes_context=True)
def notification_count(context):
    notifications = _context_unread(context)
    return notifications.count()
