from django.contrib.auth.models import User # pylint: disable=imported-auth-user
from django.core.management.base import BaseCommand, CommandError

from course.models import CourseInstance
from userprofile.models import UserProfile


class Command(BaseCommand):
    help = "Enroll students from a list file in a course"

    def add_arguments(self, parser):
        parser.add_argument(
            'course_instance_id',
            help="ID of the CourseInstance which the students are enrolled in.",
        )
        parser.add_argument(
            'student_list_file',
            help="File path to the student list file. The file should contain "
                 "one student identifier per line. The identifiers are student numbers "
                 "in the local home organization by default. "
                 "If the flag --email is given, then the identifiers are email addresses. "
                 "At any rate, only students with a student number may be enrolled in the course.",
        )
        parser.add_argument(
            '--email',
            action='store_true',
            help="If this is given, the identifiers in the student_list_file are email addresses.",
        )

    def handle(self, *args, **options):
        try:
            course_instance = CourseInstance.objects.get(id=options['course_instance_id'])
        except CourseInstance.DoesNotExist as exc:
            raise CommandError(f"CourseInstance id={options['course_instance_id']} does not exist!") from exc

        nonexistent_ids = []
        counter = 0
        try:
            with open(options['student_list_file'], 'r', encoding="utf-8") as f:
                for row in f:
                    identifier = row.strip()
                    if identifier:
                        if options['email']:
                            user = User.objects.filter(
                                email=identifier,
                            ).exclude(
                                userprofile__student_id__isnull=True,
                            ).exclude(
                                userprofile__student_id='',
                            ).first()
                            if user is None:
                                nonexistent_ids.append(identifier)
                            elif course_instance.enroll_student(user):
                                counter += 1
                        else:
                            try:
                                profile = UserProfile.get_by_student_id(identifier)
                                if course_instance.enroll_student(profile.user):
                                    counter += 1
                            except UserProfile.DoesNotExist:
                                nonexistent_ids.append(identifier)
        except FileNotFoundError as exc:
            raise CommandError(f"The student list file {options['student_list_file']} was not found!") from exc
        except OSError as e:
            self.print_results(course_instance, counter, nonexistent_ids)
            raise CommandError("Error in reading the student list file: " + str(e)) from e

        self.print_results(course_instance, counter, nonexistent_ids)


    def print_results(self, course_instance, counter, nonexistent_ids):
        if nonexistent_ids:
            self.stdout.write("The following users were not found:")
            for ni in nonexistent_ids:
                self.stdout.write(ni)

        self.stdout.write(
            f"Enrolled {counter} students in the course "
            f"{course_instance.course.url}/{course_instance.url} {str(course_instance)}.",
        )
