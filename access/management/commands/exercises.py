from django.core.management.base import BaseCommand, CommandError
from access.views import config

class Command(BaseCommand):
    args = "<course_key <exercise_key>>"
    help = "Tests configuration files syntax."
    
    def handle(self, *args, **options):

        # Check by arguments.
        if len(args) > 0:
            course_key = args[0]
            course = config.course_entry(course_key)
            if course is None:
                raise CommandError("Course not found for key: %s" % (course_key))
            self.stdout.write("Configuration syntax ok for: %s" % (course_key))
            
            if len(args) > 1:
                exercise_key = args[1]
                (_course, exercise) = config.exercise_entry(course_key, exercise_key)
                if exercise is None:
                    raise CommandError("Exercise not found for key: %s/%s" % (course_key, exercise_key))
                self.stdout.write("Configuration syntax ok for: %s/%s" % (course_key, exercise_key))
            
            else:
                (_course, exercises) = config.exercises(course_key)
                for exercise in exercises:
                    self.stdout.write("Configuration syntax ok for: %s/%s" % (course_key, exercise["key"]))
        
        # Check all.
        else:
            for course in config.courses():
                self.stdout.write("Configuration syntax ok for: %s" % (course["key"]))
                (_course, exercises) = config.exercises(course["key"])
                for exercise in exercises:
                    self.stdout.write("Configuration syntax ok for: %s/%s" % (course["key"], exercise["key"]))
