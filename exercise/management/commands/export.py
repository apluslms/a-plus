from django.core.management.base import BaseCommand, CommandError

from exercise.models import BaseExercise


class Command(BaseCommand):
    args = 'exercise_id'
    help = 'Exports submissions for an exercise.'

    def handle(self, *args, **options):
        if len(args) != 1:
            raise CommandError('Missing exercise_id')

        exercise = BaseExercise.objects.filter(id=args[0]).first()
        if not exercise:
            raise CommandError('Exercise not found.')

        submissions = list(exercise.submissions.all())

        fields = []
        for submission in submissions:
            for key, val in submission.submission_data:
                if not key in fields:
                    fields.append(key)
        fields = sorted(fields)

        header = [ 'Time', 'Email', 'Status', 'Grade' ]
        header += fields
        print(','.join(header))

        for submission in submissions:
            data = [
                str(submission.submission_time),
                submission.submitters.first().user.email,
                submission.status,
                str(submission.grade),
            ]
            values = [[] for field in fields]
            if submission.submission_data:
                for key, val in submission.submission_data:
                    values[fields.index(key)].append(val.replace('"','\''))
            data += ['"' + (';'.join(v)) + '"' for v in values]
            print(','.join(data))
