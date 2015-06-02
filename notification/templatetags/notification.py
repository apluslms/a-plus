
from django import template
from notification.models import UnreadNotifications

register = template.Library()

@register.assignment_tag
def unread_notifications(user):
    return UnreadNotifications.get_for(user)
