'''
Tools to import modules by name.
'''
from django.utils.module_loading import import_string


def import_named(course, path):
    if path.startswith('.'):
        path = 'exercises.' + course['key'] + path
    return import_string(path)
