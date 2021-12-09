from django.core.management.base import BaseCommand, CommandError

from course.models import CourseInstance
from edit_course.operations.configure import configure_content

class Command(BaseCommand):
    help = "Reload course configuration from configuration url"

    def add_arguments(self, parser):
        parser.add_argument('path', metavar="PATH", nargs='?',
                            default="def/current",
                            help="Path component of the course to be reconfigured from it's configuration url (default: 'def/current')")
        parser.add_argument('-u', '--url',
                            help="Replace current configuration url with this one")

    def handle(self, *args, **options):
        path = options['path'].strip().strip('/')
        parts = path.split('/')
        if len(parts) != 2:
            raise CommandError("Path parameter neets to be in format of <course>/<instance>")

        try:
            instance = CourseInstance.objects.get(course__url=parts[0], url=parts[1])
        except CourseInstance.DoesNotExist:
            raise CommandError("Could not find course instance with path '{}'.".format(path))

        conf_url = options['url'] or instance.configure_url
        if not conf_url:
            raise CommandError("There is no configuration url for {}. Use --url=<url> to set one.".format(instance))

        success, errors = configure_content(instance, conf_url)
        if success:
            if errors:
                self.stdout.write(self.style.WARNING("\n".join((str(e) for e in errors))))
            else:
                self.stdout.write(self.style.SUCCESS("Course update done!"))
        elif errors:
            self.stdout.write(self.style.ERROR("\n".join((str(e) for e in errors))))
            raise CommandError("Configuration failed!")
        else:
            self.stdout.write(self.style.ERROR("Failed to update"))
