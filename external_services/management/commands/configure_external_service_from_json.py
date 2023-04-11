import json

from django.core.management.base import BaseCommand, CommandError

from course.models import CourseInstance
from external_services.models import LTIService, MenuItem


class Command(BaseCommand):
    help = "Add or update a LTI Service configuration from a json file"

    def add_arguments(self, parser):
        parser.add_argument('-c', '--course', metavar="COURSE/INSTANCE",
                            help="Course selector to add the lti service to the menu")
        parser.add_argument('path', metavar="PATH_TO_JSON",
                            help="Path to a json file with a lti service configuration")

    def handle(self, *args, **options): # noqa: MC0001
        if options['course']:
            course_s = options['course'].strip().strip('/')
            if course_s == 'all':
                courses = list(CourseInstance.objects.all())
            else:
                course_p = course_s.split('/')
                if len(course_p) != 2:
                    raise CommandError("Course parameter neets to be in format of <course>/<instance> or 'all'")

                try:
                    courses = [CourseInstance.objects.get(course__url=course_p[0], url=course_p[1])]
                except CourseInstance.DoesNotExist as exc:
                    raise CommandError("Could not find course instance with path '{}'.".format(course_s)) from exc
        else:
            courses = []

        path = options['path']
        try:
            with open(path, 'r', encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as error:
            raise CommandError("Could not parse json file '{}', error: {}".format(path, error)) from error

        try:
            label = data['label']
        except KeyError as error:
            raise CommandError(
                "Could not data from json file '{}', key {} not found and is required!".format(path, error)
            ) from error

        all_ = LTIService.objects.filter(menu_label=label).all()
        if all_.count() == 1:
            instance = all_.first()
        else:
            instance = LTIService()

        try:
            instance.url = data['url']
            instance.menu_label = label
            instance.consumer_key = data['key']
            instance.consumer_secret = data['secret']
        except KeyError as error:
            raise CommandError(
                "Could not data from json file '{}', key {} not found and is required!".format(path, error)
            ) from error

        if 'icon' in data:
            instance.menu_icon_class = data['icon']

        instance.access_settings = LTIService.LTI_ACCESS.PUBLIC_API_YES
        instance.destination_region = LTIService.DESTINATION_REGION.INTERNAL
        instance.enabled = True

        created = instance.pk is None
        instance.save()

        if created:
            self.stdout.write(self.style.SUCCESS("Added new LTI service: {}".format(instance)))
        else:
            self.stdout.write(self.style.SUCCESS("Updated a LTI service: {}".format(instance)))

        for course in courses:
            if not MenuItem.objects.filter(course_instance=course, service=instance).exists():
                MenuItem.objects.create(
                    course_instance=course,
                    access=MenuItem.ACCESS.ASSISTANT,
                    service=instance,
                    menu_group_label="Local Services",
                )
                self.stdout.write(self.style.SUCCESS("Added a menu entry for {}".format(course)))
