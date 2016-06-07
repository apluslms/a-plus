from optparse import make_option
import os.path
import glob
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from access.views import config
from util.personalized import delete_pregenerated_exercise_instances, \
    prepare_pregenerated_exercises_directory, generate_exercise_instances

class Command(BaseCommand):
    help = "Pregenerate personalized exercise instances"
    args = "course_key</exercise_key>"
    option_list = BaseCommand.option_list + (
        make_option("--instances",
            action="store", dest="instances", default=10, type="int",
            help="Number of instances to generate for an exercise"),
        make_option("--keep-old",
            action="store_true", dest="keep_old", default=False,
            help="Keep existing generated instances instead of deleting them first"),
    )
    
    def handle(self, *args, **options):
        if len(args) > 0:
            if "/" in args[0]:
                course_key, exercise_key = args[0].split("/", 1)
            else:
                course_key = args[0]
                exercise_key = None
            
            course = config.course_entry(course_key)
            if course is None:
                raise CommandError("Course not found for key: %s" % (course_key))
            
            if exercise_key:
                (_course, exercise) = config.exercise_entry(course_key, exercise_key)
                if exercise is None:
                    raise CommandError("Exercise not found for key: %s/%s" % (course_key, exercise_key))
                if not ("personalized" in exercise and exercise["personalized"]):
                    raise CommandError('Exercise %s/%s is not personalized (check setting "personalized") ' \
                                       'and hence generating is impossible' % (course_key, exercise_key))
                exercises = [exercise]
            else:
                (_course, exercises) = config.exercises(course_key)
                # take only personalized exercises
                exercises = list(filter(lambda ex: "personalized" in ex and ex["personalized"], exercises))
                if not exercises:
                    raise CommandError("The course %s has no personalized exercises" % (course_key))
            
            # course and exercises have been parsed
            if options["instances"] < 1:
                raise CommandError("--instances value must be at least 1")
            
            try:
                for ex in exercises:
                    if not options["keep_old"]:
                        delete_pregenerated_exercise_instances(course, ex)
                        # check if there are any users that had been assigned to the deleted, old instances
                        for _ in glob.iglob(os.path.join(settings.PERSONALIZED_CONTENT_PATH,
                                                            course_key, "users", "*", ex["key"])):
                            self.stderr.write("Warning: previous exercise instances for %s/%s " \
                                "were deleted but there are users that have been assigned to one of those instances" % 
                                (course_key, ex["key"]))
                            break
                    
                    # ensure that base directory exists
                    prepare_pregenerated_exercises_directory(course, ex)
                    generate_exercise_instances(course, ex, options["instances"])
                    
            except Exception as e:
                raise CommandError(str(e))
            
        else:
            raise CommandError("course_key argument missing")
        
