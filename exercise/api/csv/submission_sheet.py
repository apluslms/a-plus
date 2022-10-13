from collections import OrderedDict
from typing import Any, Dict, Iterable, List, Set, Tuple

from rest_framework.request import Request
from rest_framework.reverse import reverse

from ...models import BaseExercise, Submission


def filter_best_submissions(
        submissions: Iterable[Submission],
        revealed_ids: Set[int],
        ) -> List[Submission]:
    best = {}
    forced = {}
    eid = None

    for i,s in enumerate(submissions):
        if s.exercise_id != eid:
            eid = s.exercise_id
            best[eid] = {}
            forced[eid] = {}

        if s.status == 'ready':
            user = s.submitters.first()
            uid = user.id if user else 0
            grade = s.grade if eid in revealed_ids else 0
            if s.force_exercise_points:
                # This submission is chosen as the best submission and no
                # further submissions are considered.
                best[eid][uid] = (i,grade)
                forced[eid][uid] = True
            if not forced[eid].get(uid):
                old = best[eid].get(uid)
                if not old or grade >= old[1] or s.exercise.grading_mode == BaseExercise.GRADING_MODE.LAST:
                    best[eid][uid] = (i,grade)

    filtered = []
    for ebest in best.values():
        for i,_g in ebest.values():
            filtered.append(submissions[i])
    return filtered


def submissions_sheet( # noqa: MC0001
        request: Request,
        submissions: Iterable[Submission],
        revealed_ids: Set[int],
        ) -> Tuple[List[Dict[str, Any]], List[str]]:
    DEFAULT_FIELDS = [
        'ExerciseID', 'Category', 'Exercise', 'SubmissionID', 'Time',
        'UserID', 'StudentID', 'Email', 'Status',
        'Grade', 'Penalty', 'Graded', 'GraderEmail', 'Notified', 'NSeen',
    ]
    sheet = []
    fields = []
    files = []

    def url(submission, obj):
        return reverse(
            'api:submission-files-detail',
            kwargs={
                'submission_id': submission.id,
                'submittedfile_id': obj.id,
            },
            request=request
        )

    exercise = None
    for s in submissions: # pylint: disable=too-many-nested-blocks
        if s.exercise != exercise:
            exercise = s.exercise
            if exercise.exercise_info:
                for e in exercise.exercise_info.get('form_spec', []):
                    t = e['type']
                    k = e['key']
                    if t == 'file':
                        if k not in files:
                            files.append(k)
                    elif t != 'static':
                        if k not in fields:
                            fields.append(k)

        grader = s.grader.user.email if s.grader else None

        # Find reviewer email from rubyric feedback.
        t = s.feedback
        if not grader and t and t.startswith("\n<p>\nReviewer:"):
            grader = t[t.find("<a href=\"mailto:")+16:t.find("\">")]

        n = s.notifications.first()
        row = OrderedDict([
            ('ExerciseID', exercise.id),
            ('Category', exercise.category.name),
            ('Exercise', str(exercise)),
            ('SubmissionID', s.id),
            ('Time', str(s.submission_time)),
            ('UserID', None),
            ('StudentID', None),
            ('Email', None),
            ('Status', s.status),
            ('Grade', s.grade if exercise.id in revealed_ids else 0),
            ('Penalty', s.late_penalty_applied),
            ('Graded', str(s.grading_time)),
            ('GraderEmail', grader),
            ('Notified', n is not None),
            ('NSeen', n.seen if n else False),
        ])

        if s.submission_data:
            for k,v in s.submission_data:
                if v or k not in files:
                    if k not in fields:
                        fields.append(k)
                    if k in row:
                        row[k] += "|" + str(v)
                    else:
                        row[k] = str(v)

        for f in s.files.all():
            if f.param_name not in files:
                files.append(f.param_name)
            row[f.param_name] = url(s,f)

        for i,profile in enumerate(s.submitters.all()):
            r = row.copy() if i > 0 else row
            r['UserID'] = profile.user.id
            r['StudentID'] = profile.student_id
            r['Email'] = profile.user.email
            sheet.append(r)

    return sheet, DEFAULT_FIELDS + fields + files
