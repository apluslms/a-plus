"""Django template context processors that may be enabled in settings.py (TEMPLATES)."""

from django.conf import settings

from aplus import VERSION


def aplus_version(request):
    return {
        'APLUS_VERSION': 'v' + VERSION,
    }

def gitmanager_enabled(request):
    return {
        'GITMANAGER_ENABLED': bool(settings.GITMANAGER_URL),
    }

def gitmanager_url(request):
    return {
        'GITMANAGER_URL': settings.GITMANAGER_URL,
    }
