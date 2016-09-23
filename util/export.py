from django.conf import settings
from django.core.urlresolvers import reverse


def url_to_exercise(request, course_key, exercise_key):
    return request.build_absolute_uri(
        reverse('exercise', args=[course_key, exercise_key]))


def url_to_model(request, course_key, exercise_key, parameter=None):
    return request.build_absolute_uri(
        reverse('model', args=[course_key, exercise_key, parameter or ''])
    )


def url_to_static(request, course_key, path):
    ''' Creates an URL for a path in static files '''
    return request.build_absolute_uri(
        '{}{}/{}'.format(settings.STATIC_URL, course_key, path))


def chapter(request, course, of):
    ''' Exports chapter data '''
    of['url'] = url_to_static(request, course['key'], of['static_content'])
    return of


def exercise(request, course, exercise, of):
    ''' Exports exercise data '''
    if not "title" in of and not "name" in of:
        of["title"] = exercise.get("title", "")
    if not "description" in of:
        of["description"] = exercise.get("description", "")
    if "url" in exercise:
        of["url"] = exercise["url"]
    else:
        of["url"] = url_to_exercise(request, course['key'], exercise['key'])

    of['exercise_info'] = {
        'form_spec': form_fields(exercise),
        'resources': [url_to_static(request, course['key'], p) for p in exercise.get('resource_files', [])],
    }

    if exercise.get('view_type', None) == 'access.types.stdsync.createForm':
        of['model_answer'] = url_to_model(
            request, course['key'], exercise['key']
        )
    else:
        file_names = [
            path.split('/')[-1] for path in exercise.get('model_files', [])
        ]
        of['model_answer'] = ' '.join([
            url_to_model(request, course['key'], exercise['key'], name)
            for name in file_names
        ])
    return of


def form_fields(exercise):
    ''' Describes a form that the configured exercise produces '''
    form = []
    t = exercise.get('view_type', None)

    if t == 'access.types.stdsync.createForm':
        n = 0
        for fg in exercise.get('fieldgroups', []):
            for f in fg.get('fields', []):
                field = {
                    'key': f.get('key', 'field_' + str(n)),
                    'type': f['type'],
                    'title': f['title'],
                    'required': f.get('required', False),
                }

                mods = f.get('compare_method', '').split('-')
                if 'int' in mods:
                    field['type'] = 'number'
                elif 'float' in mods:
                    field['type'] = 'number'
                elif 'regexp' in mods:
                    field['pattern'] = f['correct']
                if 'more' in f:
                    field['description'] = f['more']

                if 'options' in f:
                    titleMap = {}
                    enum = []
                    m = 0
                    for o in f['options']:
                        v = o.get('value', 'option_' + str(m))
                        titleMap[v] = o.get('label|i18n', o.get('label', ['missing']))
                        enum.append(v)
                        m += 1
                    field['titleMap'] = titleMap
                    field['enum'] = enum

                if 'extra_info' in f:
                    field.update(f['extra_info'])

                if 'class' in field:
                    field['htmlClass'] = field['class']
                    del(field['class'])

                form.append(field)
                n += 1

    elif t == 'access.types.stdasync.acceptPost':
        for f in exercise.get('fields', []):
            form.append({
                'key': f['name'],
                'type': 'textarea',
                'title': f['title'],
                'requred': f.get('required', False),
            })

    elif t == 'access.types.stdasync.acceptFiles':
        for f in exercise.get('files', []):
            form.append({
                'key': f['field'],
                'type': 'file',
                'title': f['name'],
                'required': f.get('required', True),
            })
    return form
