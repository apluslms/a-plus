import json
import re

from django.core.management.base import BaseCommand, CommandError

from course.models import CourseInstance, LearningObjectCategory
from ...models import BaseExercise, LearningObjectDisplay


class Command(BaseCommand):
    help = 'Exports submission data.'

    def add_arguments(self, parser):
        parser.add_argument('args', nargs='+',
            help='One of exercise/exercises/category/course/json/views/results '
                 'followed by object id(s)')

    def handle(self, *args, **options):
        if len(args) < 2:
            raise CommandError('Missing arguments! Check --help')
        if args[0] == 'exercise':
            self.export_exercise(args[1])
        elif args[0] == 'exercises':
            self.export_exercises(args[1:])
        elif args[0] == 'category':
            self.export_category(args[1])
        elif args[0] == 'course':
            self.export_course(args[1])
        elif args[0] == 'json':
            self.export_json(args[1])
        elif args[0] == 'views':
            self.export_views(args[1])
        else:
            raise CommandError('Unknown argument!')

    def export_exercises(self, eids):
        fields = set()
        for eid in eids:
            exercise = BaseExercise.objects.get(id=eid)
            for s in exercise.submissions.all():
                if s.submission_data:
                    for key, _val in s.submission_data:
                        fields.add(key)
        fields = sorted(fields)
        n = 0
        for eid in eids:
            self.export_exercise(eid, n == 0, fields)
            n += 1

    def export_category(self, cid):
        category = LearningObjectCategory.objects.get(id=cid)
        self.export_exercises(list(e.id for e in category.learning_objects.all()))

    def export_exercise(self, eid, print_header=True, fields=None):
        exercise = BaseExercise.objects.filter(id=eid).first()
        if not exercise:
            raise CommandError('Exercise {} not found.'.format(eid))

        students = [u['id'] for u in exercise.course_module.course_instance.students.values('id')]
        submissions = [s for s in exercise.submissions.all() if s.submitters.first().id in students]

        if fields is None:
            fields = set()
            for s in submissions:
                if s.submission_data:
                    for key,val in s.submission_data:
                        fields.add(key)
            fields = sorted(fields)

        header = [ 'EID', 'Exercise', 'Time', 'UID', 'Student ID', 'Email', 'Status', 'Grade']
        header += fields
        if print_header:
            self.print_row(header)

        for submission in submissions:
            profile = submission.submitters.first()
            data = [
                str(exercise.id),
                '"' + ((str(exercise.parent) + ' ' + str(exercise)) if exercise.parent else str(exercise)) + '"',
                str(submission.submission_time),
                str(profile.id),
                profile.student_id or "",
                profile.user.email or "",
                submission.status,
                str(submission.grade),
                #self.strip_html_tags(submission.feedback),
                #submission.assistant_feedback,
            ]
            values = [[] for field in fields]
            if submission.submission_data:
                for key,val in submission.submission_data:
                    values[fields.index(key)].append(val.replace('"','\'').replace('\n','\\n').replace('\r',''))
            data += ['"' + (';'.join(v)) + '"' for v in values]
            self.print_row(data)

    def export_course(self, cid):
        instance = CourseInstance.objects.filter(id=cid).first()
        if not instance:
            raise CommandError('Course instance not found.')
        students = [u['id'] for u in instance.students.values('id')]

        self.print_row([ 'Time', 'UID', 'Email', 'MID', 'Module', 'EID', 'Exercise', 'Status', 'Grade' ])

        for exercise in BaseExercise.objects.filter(course_module__course_instance=instance).all():
            module = exercise.course_module
            submissions = [s for s in exercise.submissions.all() if s.submitters.first().id in students]
            for submission in submissions:
                profile = submission.submitters.first()
                self.print_row([
                    str(submission.submission_time),
                    str(profile.id),
                    profile.user.email,
                    str(module.id),
                    str(module),
                    str(exercise.id),
                    str(exercise),
                    submission.status,
                    str(submission.grade),
                ])

    def export_json(self, cid):
        instance = CourseInstance.objects.filter(id=cid).first()
        if not instance:
            raise CommandError('Course instance not found.')
        students = [u['id'] for u in instance.students.values('id')]

        data = []
        for exercise in BaseExercise.objects.filter(course_module__course_instance=instance).all():
            module = exercise.course_module
            submissions = [s for s in exercise.submissions.all() if s.submitters.first().id in students]
            for submission in submissions:
                profile = submission.submitters.first()
                data.append({
                    'Time': str(submission.submission_time),
                    'UID': str(profile.id),
                    'Email': profile.user.email,
                    'MID': str(module.id),
                    'Module': str(module),
                    'EID': str(exercise.id),
                    'Exercise': str(exercise),
                    'Status': submission.status,
                    'Grade': str(submission.grade),
                    'Submission data': submission.submission_data or [],
                    'Grading data': submission.grading_data or {},
                })
        self.stdout.write(json.dumps(data))

    def export_views(self, cid):
        instance = CourseInstance.objects.filter(id=cid).first()
        if not instance:
            raise CommandError('Course instance not found.')

        students = [u['id'] for u in instance.students.values('id')]
        displays = [d for d in (LearningObjectDisplay.objects
            .prefetch_related('profile', 'learning_object')
            .all()
        ) if d.profile.id in students]

        self.print_row(['Time', 'UID', 'Email', 'MID', 'Module', 'EID', 'Exercise'])
        for d in displays:
            module = d.learning_object.course_module
            self.print_row([
                str(d.timestamp),
                str(d.profile.id),
                d.profile.user.email,
                str(module.id),
                str(module),
                str(d.learning_object.id),
                str(d.learning_object),
            ])

    def print_row(self, fields, quote=False):
        if quote:
            fields = ['"{}"'.format(self.quote(f)) for f in fields]
        self.stdout.write(','.join(fields))

    def quote(self, value):
        for m,s in [('"','\''),('\n','\\n'),('\r','\\r'),('\t','\\t')]:
            value = value.replace(m, s)
        return value

    def strip_html_tags(self, value):
        return re.sub('<[^>+?]>', '', value)
