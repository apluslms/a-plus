from django.core.management.base import BaseCommand
from django.db import transaction

from exercise.submission_models import Submission, recompute_exercise_user_points


class Command(BaseCommand):
    help = "Backfill ExerciseUserPoints stats from existing submissions."

    def add_arguments(self, parser):
        parser.add_argument('--course', type=int, help='Optional course instance id to limit backfill')
        parser.add_argument('--batch', type=int, default=1000, help='Batch size for processing unique pairs')

    def handle(self, *args, **options):
        course = options.get('course')
        batch = options['batch']

        qs = Submission.objects.all()
        if course:
            qs = qs.filter(exercise__course_module__course_instance_id=course)

        pairs = (
            qs.values_list('exercise_id', 'submitters__id')
              .distinct()
        )

        total = 0
        buf = []
        for exercise_id, submitter_id in pairs.iterator():
            if submitter_id is None:
                continue
            buf.append((exercise_id, submitter_id))
            if len(buf) >= batch:
                self._process(buf)
                total += len(buf)
                self.stdout.write(f"Processed {total} pairs...")
                buf = []
        if buf:
            self._process(buf)
            total += len(buf)

        self.stdout.write(self.style.SUCCESS(f"Backfill complete. Total pairs: {total}"))

    @staticmethod
    def _process(pairs):
        with transaction.atomic():
            for exercise_id, submitter_id in pairs:
                recompute_exercise_user_points(exercise_id, submitter_id)
