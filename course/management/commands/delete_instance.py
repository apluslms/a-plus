from django.core.management.base import BaseCommand
from django.db.models.query import QuerySet
from course.models import CourseInstance
import datetime

class Command(BaseCommand):
    help = "Delete course instance along with related data (exercises, submissions, etc)."

    def add_arguments(self, parser):
        parser.add_argument(
            '-c',
            '--course-instance',
            type=int,
            nargs='*',
            help='Course instance ID(s) to be deleted. Multiple IDs can be given.',
        )
        parser.add_argument(
            '-e',
            '--ending-since',
            type=int,
            help='Delete all course instances that ended since N days ago.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Do not delete anything, but show which instances would be deleted.',
        )

    def handle(self, *args, **options):
        course_instances: QuerySet[CourseInstance] = CourseInstance.objects.none()

        if options['ending_since']:
            deletetime = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
                days=options['ending_since']
            )
            course_instances = CourseInstance.objects.filter(ending_time__lt=deletetime)

        if options['course_instance']:
            for i in options['course_instance']:
                course_instances = course_instances.union(CourseInstance.objects.filter(id=i))

        if options['dry_run']:
            self.stdout.write('This is just a dry run. Nothing will be deleted.')

        for c in course_instances:
            self.stdout.write(f"deleting instance {c}")
            if not options['dry_run']:
                c.delete()
