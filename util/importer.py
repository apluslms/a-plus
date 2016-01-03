'''
Tools to import modules by name.
'''
from django.utils.module_loading import import_by_path


def import_named(course, path):
    if path.startswith('.'):
        path = 'exercises.' + course['key'] + path
    try:
        return import_by_path(path)
    except ImproperlyConfigured as e:
        raise ConfigError("Invalid function path in exercise configuration.", e)
