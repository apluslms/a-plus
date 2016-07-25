from django.conf import settings


def url_to_course(request, course_key, path):
    ''' Creates an URL for a course path '''
    return request.build_absolute_uri(
        '/{}/{}'.format(course_key, path)
    )


def url_to_static(request, course_key, path):
    ''' Creates an URL for a path in static files '''
    return request.build_absolute_uri(
        '{}{}/{}'.format(settings.STATIC_URL, course_key, path)
    )


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
    print(course['key'], exercise['key'])
    of['url'] = url_to_course(request, course['key'], exercise['key'])
    of['exercise_info'] = {
        'form_spec': form_fields(exercise),
        'resources': [url_to_static(request, course['key'], p) for p in exercise.get('resource_files', [])],
    }
    of['model_answer'] = ' '.join([url_to_static(request, course['key'], p) for p in exercise.get('model_files', [])])
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
                if 'more' in f:
                    field['description'] = f['more']
                if 'options' in f:
                    titleMap = {}
                    enum = []
                    m = 0
                    for o in f['options']:
                        v = o.get('value', 'option_' + str(m))
                        titleMap[v] = o['label']
                        enum.append(v)
                        m += 1
                    field['titleMap'] = titleMap
                    field['enum'] = enum
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
