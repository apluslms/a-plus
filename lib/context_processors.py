"""Django template context processors that may be enabled in settings.py (TEMPLATES)."""

from aplus import VERSION


def aplus_version(request):
    return {
        'APLUS_VERSION': 'v' + VERSION,
    }
