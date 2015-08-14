from django.core.management.base import BaseCommand, CommandError
from access.config import ConfigParser
from grader.runactions import runactions
from util.files import create_submission_dir, submission_file_path
from util.templates import template_to_str
import os, shutil

class Command(BaseCommand):
    args = "course_key exercise_key <submit_file submit_file ...>"
    help = "Grades a given exercise submission as it would be in the grading queue."
    
    def handle(self, *args, **options):
        
        config = ConfigParser()
        
        # Check arguments.
        if len(args) < 2:
            raise CommandError("Required arguments missing: course_key exercise_key")
        course_key = args[0]
        exercise_key = args[1]
        
        # Get exercise configuration.
        (course, exercise) = config.exercise_entry(course_key, exercise_key)
        if course is None:
            raise CommandError("Course not found for key: %s" % (course_key))    
        if exercise is None:
            raise CommandError("Exercise not found for key: %s/%s" % (course_key, exercise_key))
        self.stdout.write('Exercise configuration retrieved.')

        # Check exercise type.
        if not "actions" in exercise:
            raise CommandError("Cannot grade: exercise does not configure asynchronous actions")
        
        # Create submission.
        sdir = create_submission_dir(course, exercise)
        if len(args) == 2:
            os.makedirs(sdir + "/user")
        for n in range(2, len(args)):
            name = args[n]
            
            # Copy individual files.
            if os.path.isfile(name):
                submit_path = submission_file_path(sdir, os.path.basename(name))
                shutil.copy2(name, submit_path)
            
            # Copy a directory.
            elif os.path.isdir(name):
                if len(args) != 3:
                    raise CommandError("Can only submit one directory or multiple files.")
                shutil.copytree(name, sdir + "/user", True)
            
            else:
                raise CommandError("Submit file not found: %s" % (name))
        
        # Run actions.
        r = runactions(course, exercise, sdir)
        self.stdout.write("Response body:")
        self.stdout.write(template_to_str(course, exercise, r["template"], r["result"]))
