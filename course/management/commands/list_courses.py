import datetime

from django.core.management.base import BaseCommand, CommandError

from course.models import CourseInstance
from exercise.models import Submission


class Command(BaseCommand):
    help = "List all courses (course instances)"

    def add_arguments(self, parser):
        parser.add_argument(
            '-f',
            '--fmt',
            metavar="FMT",
            default="{c.url}/{i.url}  {i}",
            help="Python format string used to print a single instance. "
                 "Course is in var 'c' and instance in var 'i'. "
                 "(e.g. '{c.id}:{i.id} {i}')",
        )
        parser.add_argument(
            '-a',
            '--starts-after',
            type=datetime.datetime.fromisoformat,
            metavar='YYYY-MM-DD HH:MM:SS +HH:MM',
            help="Include only course instances that start after this date. "
                 "Give the timestamp in the ISO 8601 format: YYYY-MM-DD HH:MM:SS +HH:MM. "
                 "If you do not specify the timezone, UTC +00:00 is assumed.",
        )
        parser.add_argument(
            '-b',
            '--starts-before',
            type=datetime.datetime.fromisoformat,
            metavar='YYYY-MM-DD HH:MM:SS +HH:MM',
            help="Include only course instances that start before this date. "
                 "Give the timestamp in the ISO 8601 format: YYYY-MM-DD HH:MM:SS +HH:MM. "
                 "If you do not specify the timezone, UTC +00:00 is assumed.",
        )
        parser.add_argument(
            '-e',
            '--enrolled-students',
            action='store_true',
            help="If set, include the number of enrolled students in each "
                 "course instance. The format string in the --fmt option may "
                 "use the variable 'e'.",
        )
        parser.add_argument(
            '-s',
            '--submissions',
            action='store_true',
            help="If set, include the total number of exercise submissions "
                 "from the enrolled students in each course instance. "
                 "The format string in the --fmt option may use the variable 's'.",
        )

    def handle(self, *args, **options):
        starts_after = options.get('starts_after')
        starts_before = options.get('starts_before')

        instances = CourseInstance.objects.all()
        if starts_after:
            if starts_after.tzinfo is None: # naive datetime, make it normal time UTC +0
                starts_after = starts_after.replace(tzinfo=datetime.timezone.utc)
            instances = instances.filter(starting_time__gte=starts_after)
        if starts_before:
            if starts_before.tzinfo is None:
                starts_before = starts_before.replace(tzinfo=datetime.timezone.utc)
            instances = instances.filter(starting_time__lt=starts_before)
        instances = instances.order_by('course__code', 'instance_name')

        fmt = options['fmt']
        if '{e}' not in fmt and options['enrolled_students']:
            fmt += ' - enrolled {e}'
        if '{s}' not in fmt and options['submissions']:
            fmt += ' - submissions {s}'

        i = -1
        for i, instance in enumerate(instances):
            num_enrolled = None
            if options['enrolled_students']:
                num_enrolled = instance.students.exclude(
                    id__in=instance.assistants.all(),
                ).exclude(
                    id__in=instance.teachers.all(),
                ).count()

            num_submissions = None
            if options['submissions']:
                num_submissions = Submission.objects.filter(
                    exercise__course_module__course_instance=instance,
                ).exclude(
                    submitters__in=instance.assistants.all(),
                ).exclude(
                    submitters__in=instance.teachers.all(),
                ).count()

            self.stdout.write(fmt.format(i=instance, c=instance.course, e=num_enrolled, s=num_submissions))
        if i < 0:
            raise CommandError("No course instances in db")
