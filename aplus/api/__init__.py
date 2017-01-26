from django.core.urlresolvers import reverse
from rest_framework.settings import api_settings

def api_reverse(name, kwargs=None, **extra):
    if not kwargs:
        kwargs = {}
    kwargs.setdefault('version', api_settings.DEFAULT_VERSION)
    return reverse('api:' + name, kwargs=kwargs, **extra)
