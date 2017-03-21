from collections import OrderedDict


def filter_to_best(submissions):
    best = {}
    eid = None

    for s in submissions.order_by('exercise_id', 'submission_time'):
        if s.exercise_id != eid:
            eid = s.exercise_id
            best[eid] = {}

        if s.status == 'ready':
            user = s.submitters.first()
            uid = user.id if user else 0
            old = best[eid].get(uid)
            if not old or s.grade >= old[1]:
                best[eid][uid] = (s.id,s.grade)

    ids = []
    for ebest in best.values():
        ids.extend([i for i,g in ebest.values()])
    return submissions.filter(id__in=ids)


def submitted_fields(submissions):
    fields = []
    files = []
    exercise = None
    for s in submissions.order_by('exercise_id', 'id'):

        if s.exercise != exercise:
            exercise = s.exercise
            spec = exercise.exercise_info.get('form_spec')
            if not spec is None:
                for k in [e['key'] for e in spec]:
                    if not k in fields:
                        fields.append(k)

        if s.submission_data:
            for k,v in s.submission_data:
                if not k in fields:
                    fields.append(k)

        for f in s.files.all():
            if not f.param_name in files:
                files.append(f.param_name)

    return fields,files


DEFAULT_FIELDS = [
    'EID', 'Exercise', 'UID', 'StudentID', 'Email', 'ID', 'Time', 'Status',
    'Grade', 'Penalty', 'Graded', 'Notified', 'NSeen',
]


def serialize_submissions(request, fields, files, submissions):

    def url(obj):
        return request.build_absolute_uri(obj.get_absolute_url())

    sheet = []
    for s in submissions.order_by('exercise_id', 'id'):
        exercise = s.exercise
        n = s.notifications.first()
        row = OrderedDict([
            ('EID', exercise.id),
            ('Exercise', str(exercise)),
            ('UID', None),
            ('StudentID', None),
            ('Email', None),
            ('ID', s.id),
            ('Time', str(s.submission_time)),
            ('Status', s.status),
            ('Grade', s.grade),
            ('Penalty', s.late_penalty_applied),
            ('Graded', str(s.grading_time)),
            ('Notified', not n is None),
            ('NSeen', n.seen if n else False),
        ])

        if s.submission_data:
            m = {k: v for k,v in s.submission_data}
            for k in fields:
                row[k] = m.get(k, None)

        m = {f.param_name: url(f) for f in s.files.all()}
        for k in files:
            row[k] = m.get(k, None)

        for profile in s.submitters.all():
            row['UID'] = profile.user.id
            row['StudentID'] = profile.student_id
            row['Email'] = profile.user.email
            sheet.append(row)

    return sheet
