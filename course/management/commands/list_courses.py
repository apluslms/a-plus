from django.core.management.base import BaseCommand, CommandError

from course.models import CourseInstance

class Command(BaseCommand):
    help = "List all courses (course instances)"

    def add_arguments(self, parser):
        parser.add_argument('-f', '--fmt', metavar="FMT",
                            default="{c.url}/{i.url}  {i}",
                            help="Python format string used to print a single instance. "
                                 "Course is in var 'c' and instance in var 'i'. "
                                 "(e.g. '{c.id}:{i.id} {i}')")

    def handle(self, *args, **options):
        instances = CourseInstance.objects.all().order_by('course__code', 'instance_name')
        fmt = options['fmt']

        i = -1
        for i, instance in enumerate(instances):
            self.stdout.write(fmt.format(i=instance, c=instance.course))
        if i < 0:
            raise CommandError("No course instances in db")

