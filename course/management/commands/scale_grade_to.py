from django.core.management.base import BaseCommand, CommandError
from django.utils.six.moves import input
from django.core.exceptions import ObjectDoesNotExist

from course.models import CourseInstance
from exercise.submission_models import Submission
from userprofile.models import UserProfile

class Command(BaseCommand):
    args = 'course/models/courseinstance_id userprofile/userprofile_id 0-100'
    help = 'Scale student\'s all submissions grades on a given course instance.'

    def handle(self, *args, **options):
        if len(args) == 3:
            try:
                instance = CourseInstance.objects.get(id=args[0])
                student = UserProfile.objects.get(id=args[1])
            except ObjectDoesNotExist:               
                raise CommandError('Given student or instance does not exist!')
            percentage = int(args[2])
            if percentage < 0 or percentage > 100:
                raise CommandError('Scale percentage must be an integer in 0-100 range!')
            confirm = input("You are about to scale the grades for student '{}'\non the course instance '{}'\nto {} %.\nType 'yes' to confirm. YOU CAN'T UNDO THIS!\n".format(student,instance,percentage))
            if confirm == 'yes':
                submissions_changed = 0
                for submission in student.submissions.all():
                    if submission.exercise.course_instance == instance:
                        original_grade = submission.grade
                        submission.scale_grade_to(percentage)
                        submission.save()
                        submissions_changed += 1
                        self.stdout.write('Submission id {}: {} => {}'.format(submission.id, original_grade, submission.grade))
                self.stdout.write('{} submission grades were changed'.format(submissions_changed))
            else:
                self.stdout.write('No grades were changed')
        else:
            raise CommandError('Invalid number of arguments!')