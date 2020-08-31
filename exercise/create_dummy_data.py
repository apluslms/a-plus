from datetime import datetime, timedelta
import sys
import os
import string
import random
from math import log10, ceil
import logging

import django
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.datastructures import MultiValueDict

logger = logging.getLogger('aplus.testing')


def create_syllable(length=3):
    vowels = 'aeiou'
    consonants = [l for l in string.ascii_lowercase if l not in vowels]
    choices = [vowels, consonants]
    random.shuffle(choices)
    syllable = ''
    for _ in range(length):
        syllable += random.choice(choices[0])
        choices = choices[::-1]
    return syllable

def create_name(length_in_syllables=2):
    return ''.join(create_syllable() for _ in range(length_in_syllables))

def create_students(students_num):
    students = []
    used_usernames = set()
    used_student_ids = set()
    for _ in range(students_num):
        first_name = create_name()
        last_name = create_name()
        username = last_name[:6] + first_name[0] + '0'
        while username in used_usernames:
            new_ordinal = int(username[6:]) + 1
            username = username[:7] + str(new_ordinal)
        used_usernames.add(username)

        student_id_max = 10**ceil(log10(students_num)) - 1
        gen_student_id = lambda: str(random.randint(0, student_id_max)).zfill(len(str(student_id_max)))
        student_id = gen_student_id()
        while student_id in used_student_ids:
            student_id = gen_student_id()
        used_student_ids.add(student_id)

        user = User.objects.create(
            username=username,
            email=username+'@localhost',
            first_name=first_name,
            last_name=last_name)
        user.set_password(username)
        user.save()
        user.userprofile.student_id = student_id
        user.userprofile.save()
        students.append(user)
        logger.info("New student User id was %s, UserProfile id was %s", user.pk, user.userprofile.pk)
    return students


def create_course_until_exercises(exercises_num):
    course = Course.objects.create(
        name="test course",
        code="123456",
        url="test_course"
    )

    #logger.info("Creating dummy module open {} to {}".format(today, far_in_the_future))

    course_instance = CourseInstance.objects.create(
        instance_name="Testing instance @ " + str(today),
        starting_time=today,
        ending_time=far_in_the_future,
        course=course,
        url="T-00.1000_d1",
        view_content_to=CourseInstance.VIEW_ACCESS.ENROLLMENT_AUDIENCE,
    )

    exercises = []
    course_module_object = CourseModule.objects
    for m in range(1, 3):
        course_module = course_module_object.create(
            name=str(m)+". test module",
            url="test-module-"+str(m),
            points_to_pass=20,
            course_instance=course_instance,
            opening_time=today,
            closing_time=module_closing_time
        )

        learning_object_category = LearningObjectCategory.objects.create(
            name="test category " + str(m),
            course_instance=course_instance,
            points_to_pass=10,
            accept_unofficial_submits=True,
        )

        difficulties = ["", "A"]
        for i in range(exercises_num):
            ordinal = i + 1
            exercise = BaseExercise.objects.create(
                order=ordinal,
                name="test exercise {}".format(ordinal),
                course_module=course_module,
                category=learning_object_category,
                url="s" + str(ordinal),
                max_submissions=3,
                max_points=50,
                points_to_pass=30,
                difficulty=difficulties[(i % 2)],
                service_url="/testServiceURL",
            )
            exercises.append(exercise)

    return exercises, course_instance


def enroll(students, course_instance):
    for student in students:
        Enrollment.objects.create(
            course_instance=course_instance,
            user_profile=student.userprofile
        )


def create_submissions(students, exercises, grader):
    for student in students:
        for exercise in exercises:
            max_points = exercise.max_points
            submission_count = random.choice([0, 1, 1, 1, 1, 2, 2, 5])
            is_unofficial = (random.randint(0, 6) == 5)
            for i in range(submission_count):
                points_got = random.randint(0, max_points)
                submission = Submission.objects.create(
                    exercise=exercise,
                    grader=grader.userprofile,
                )
                submission.submitters.add(student.userprofile)
                if is_unofficial:
                    submission.status = submission.STATUS.UNOFFICIAL
                submission.set_points(points_got, max_points)
                submission.set_ready()
                submission.save()

def do_id_desync():
    user_table_name = User._meta.db_table
    user_id_column_name = User._meta.pk.column
    userprofile_table_name = UserProfile._meta.db_table
    userprofile_id_column_name = UserProfile._meta.pk.column
    with connection.cursor() as c:
        if connection.vendor == 'postgresql':
            c.execute("SELECT pg_get_serial_sequence(%s, %s);", [user_table_name, user_id_column_name])
            user_id_sequence_name = c.fetchone()[0]
            c.execute("SELECT setval(%s, 999);", [user_id_sequence_name])  # Sets value, returns set value
            user_id_cur_value = c.fetchone()[0]

            c.execute("SELECT pg_get_serial_sequence(%s, %s);", [userprofile_table_name, userprofile_id_column_name])
            userprofile_id_sequence_name = c.fetchone()[0]
            c.execute("SELECT nextval(%s);", [userprofile_id_sequence_name])  # Increments value, returns that next value
            userprofile_id_cur_value = c.fetchone()[0]

            logger.info("Current value for User ids: %s", ' '*7 + str(user_id_cur_value))
            logger.info("Current value for UserProfile ids: %s", userprofile_id_cur_value)
            assert(user_id_cur_value != userprofile_id_cur_value)
        else:
            raise InterfaceError("Vendor {} is not configured for autoincrement desync. See create_dummy_data.py.".format(connection.vendor))


if __name__ == '__main__':
    students_num = 120
    exercises_num = 3
    desync_ids = True  # Cause corresponding UserProfile and User objects to not match
                       # To test whether certain parts of the service depend on them matching

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aplus.settings")
    sys.path.insert(0, '')
    django.setup()

    # These imports possible after setup
    from django.contrib.auth.models import User
    from course.models import Course, CourseInstance, CourseModule, \
        LearningObjectCategory, Enrollment
    from exercise.models import BaseExercise, \
        Submission
    from userprofile.models import UserProfile
    from django.db.utils import InterfaceError
    from django.db import connection, transaction

    if desync_ids:
        do_id_desync()

    grader = User(username="grader")
    grader.set_password("graderPassword")
    grader.save()

    today = timezone.now()
    module_closing_time = today + timedelta(days=30)
    far_in_the_future = today + timedelta(days=10*365.2425)

    students = create_students(students_num)
    exercises, course_instance = create_course_until_exercises(exercises_num)
    enroll(students, course_instance)
    create_submissions(students, exercises, grader)
