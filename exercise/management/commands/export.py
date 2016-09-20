import json, base64
from django.core.management.base import BaseCommand, CommandError

from course.models import CourseInstance
from ...models import BaseExercise, LearningObjectDisplay
from ...exercise_summary import ResultTable


class Command(BaseCommand):
    args = 'exercise/course/json/views/results id'
    help = 'Exports submission data.'

    def handle(self, *args, **options):
        if len(args) != 2:
            raise CommandError('Missing arguments: exercise/course/json/views/results id')
        if args[0] == 'exercise':
            self.export_exercise(args[1])
        elif args[0] == 'course':
            self.export_course(args[1])
        elif args[0] == 'json':
            self.export_json(args[1])
        elif args[0] == 'views':
            self.export_views(args[1])
        elif args[0] == 'results':
            self.export_results(args[1])
        else:
            raise CommandError('Unknown argument!')

    def export_exercise(self, eid):
        exercise = BaseExercise.objects.filter(id=eid).first()
        if not exercise:
            raise CommandError('Exercise not found.')

        students = [u['id'] for u in exercise.course_module.course_instance.students.values('id')]
        submissions = [s for s in exercise.submissions.all() if s.submitters.first().id in students]

        fields = []
        for submission in submissions:
            for key, val in submission.submission_data:
                if not key in fields:
                    fields.append(key)
        fields = sorted(fields)

        header = [ 'Time', 'Email', 'Status', 'Grade' ]
        header += fields
        self.print_row(header)

        for submission in submissions:
            profile = submission.submitters.first()
            data = [
                str(submission.submission_time),
                profile.user.email,
                submission.status,
                str(submission.grade),
            ]
            values = [[] for field in fields]
            if submission.submission_data:
                for key, val in submission.submission_data:
                    values[fields.index(key)].append(val.replace('"','\''))
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

    def export_results(self, cid):
        instance = CourseInstance.objects.filter(id=cid).first()
        if not instance:
            raise CommandError('Course instance not found.')
        table = ResultTable(instance)

        labels = ['UID','Email','Name']
        labels.extend([str(e) for e in table.exercises])
        labels.append('Total')
        self.print_row(labels)

        for student in table.students:
            row = [str(student.id), student.user.email, student.user.first_name + ' ' + student.user.last_name]
            points = [table.results[student.id][exercise.id] for exercise in table.exercises]
            row.extend([str(p) if p else '0' for p in points])
            row.append(str(sum(p for p in points if p is not None)))
            self.print_row(row)

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
        print(json.dumps(data))

    def export_views(self, cid):
        instance = CourseInstance.objects.filter(id=cid).first()
        if not instance:
            raise CommandError('Course instance not found.')

        students = [u['id'] for u in instance.students.values('id')]
        displays = [d for d in LearningObjectDisplay.objects.prefetch_related('profile', 'learning_object').all() if d.profile.id in students]

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
            fields = ['"{}"'.format(f.replace('"','\'')) for f in fields]
        print(','.join(fields))
