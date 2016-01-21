'''
Tools to import modules by name.
'''
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_by_path


class ImportError(Exception):
    '''
    Failed to import.
    '''
    def __init__(self, value, error=None):
        self.value = value
        self.error = error

    def __str__(self):
        if self.error is not None:
            return "%s: %s" % (repr(self.value), repr(self.error))
        return repr(self.value)


def import_named(course, path):
    if path.startswith('.'):
        path = 'exercises.' + course['key'] + path
    try:
        return import_by_path(path)
    except ImproperlyConfigured as e:
        raise ImportError("Invalid function path in exercise configuration.", e)
