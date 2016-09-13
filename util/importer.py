'''
Tools to import modules by name.
'''
from django.utils.module_loading import import_string


def import_named(course, path):
    if path.startswith('.'):
        try:
            return import_string('exercises.' + course['key'] + path)
        except:
            return import_string('courses.' + course['key'] + path)
    return import_string(path)
