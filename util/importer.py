'''
Tools to import modules by name.
'''
from django.utils.module_loading import import_string

from access import config


def import_named(course, path):
    if path.startswith('.'):
        path = config.DIR.split('/')[-1] + '.' + course['key'] + path
    return import_string(path)
