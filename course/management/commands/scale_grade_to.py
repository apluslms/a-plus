from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist

from course.models import CourseInstance
from userprofile.models import UserProfile

class Command(BaseCommand):
    help = 'Scale student\'s all submissions grades on a given course instance.'

    def add_arguments(self, parser):
        parser.add_argument('course_instance_id', help='Course instance id')
        parser.add_argument('userprofile_id', help='Userprofile id')
        parser.add_argument('percentage', type=int, help='Percentage 0-100 for scaling')

    def handle(self, *args, **options):
        try:
            instance = CourseInstance.objects.get(id=options['course_instance_id'])
            student = UserProfile.objects.get(id=options['userprofile_id'])
        except ObjectDoesNotExist as exc:
            raise CommandError('Given student or instance does not exist!') from exc
        percentage = options['percentage']
        if percentage < 0 or percentage > 100:
            raise CommandError('Scale percentage must be an integer in 0-100 range!')
        confirm = input(
            "You are about to scale the grades for student '{}'\n"
            "on the course instance '{}'\nto {} %.\n"
            "Type 'yes' to confirm. YOU CAN'T UNDO THIS!\n".format(student,instance,percentage)
        )
        if confirm == 'yes':
            submissions_changed = 0
            for submission in student.submissions.all():
                if submission.exercise.course_instance == instance:
                    original_grade = submission.grade
                    submission.scale_grade_to(percentage)
                    submission.save()
                    submissions_changed += 1
                    self.stdout.write(
                        'Submission id {}: {} => {}'.format(submission.id, original_grade, submission.grade)
                    )
            self.stdout.write('{} submission grades were changed'.format(submissions_changed))
        else:
            self.stdout.write('No grades were changed')
