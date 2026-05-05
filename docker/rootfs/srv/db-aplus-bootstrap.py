import os
import random
import sys

from datetime import timedelta

import django

from django.utils import timezone


LOCAL_ORGANIZATION = 'aalto.fi'
NUM_USERS = 500


def read_list_file(filepath):
    rows = []
    with open(filepath) as f:
        for line in f:
            rows.append(line.strip())
    return rows


def create_default_users():
    from django.contrib.auth.models import User

    ur = User.objects.create(
        username="root",
        email="root@localhost.invalid",
        first_name="Ruth",
        last_name="Robinson",
        is_superuser=True,
        is_staff=True,
    )
    ur.set_password("root")
    ur.save()
    ur.userprofile.student_id = "<admin>"
    ur.userprofile.organization = LOCAL_ORGANIZATION
    ur.userprofile.save()

    uad = User.objects.create(
        username="admin",
        email="admin@localhost.invalid",
        first_name="Admin",
        last_name="User",
        is_superuser=True,
        is_staff=True,
    )
    uad.set_password("admin")
    uad.save()
    uad.userprofile.student_id = ""
    uad.userprofile.organization = LOCAL_ORGANIZATION
    uad.userprofile.save()

    ut = User.objects.create(
        username="teacher",
        email="teacher@localhost.invalid",
        first_name="Terry",
        last_name="Teacher",
    )
    ut.set_password("teacher")
    ut.save()
    ut.userprofile.student_id = "<teacher>"
    ut.userprofile.organization = LOCAL_ORGANIZATION
    ut.userprofile.save()

    ua = User.objects.create(
        username="assistant",
        email="assistant@localhost.invalid",
        first_name="Andy",
        last_name="Assistant",
    )
    ua.set_password("assistant")
    ua.save()
    ua.userprofile.student_id = "133701"
    ua.userprofile.organization = LOCAL_ORGANIZATION
    ua.userprofile.save()

    us = User.objects.create(
        username="student",
        email="student@localhost.invalid",
        first_name="Stacy",
        last_name="Student",
    )
    us.set_password("student")
    us.save()
    us.userprofile.student_id = "123456"
    us.userprofile.organization = LOCAL_ORGANIZATION
    us.userprofile.save()

    ue = User.objects.create(
        username="unenrolled",
        email="unenrolled@localhost.invalid",
        first_name="Union",
        last_name="Unenrolled",
    )
    ue.set_password("unenrolled")
    ue.save()
    ue.userprofile.student_id = "987654"
    ue.userprofile.organization = LOCAL_ORGANIZATION
    ue.userprofile.save()

    # List of common names in England adapted from Office for National Statistics.
    # https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages/livebirths/datasets/babynamesenglandandwalesbabynamesstatisticsboys
    # https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages/livebirths/datasets/babynamesenglandandwalesbabynamesstatisticsgirls
    first_names = read_list_file('/srv/first_names.txt')
    len_first_names = len(first_names)
    rand = random.Random(846793)
    rand.shuffle(first_names)

    last_names = read_list_file('/srv/last_names.txt')
    len_last_names = len(last_names)
    rand.shuffle(last_names)

    students = []
    for i in range(1, NUM_USERS + 1):
        u = User.objects.create_user(
            f'student{i}',
            email=f'student{i}@localhost.invalid',
            password=f'student{i}',
            first_name=first_names[(i - 1) % len_first_names],
            last_name=last_names[(i - 1) % len_last_names],
        )
        u.userprofile.student_id = f"1111{i:04}"
        u.userprofile.organization = LOCAL_ORGANIZATION
        u.userprofile.save()
        students.append(u.userprofile)

    return {
        'root': ur.userprofile,
        'admin': uad.userprofile,
        'teacher': ut.userprofile,
        'assistant': ua.userprofile,
        'student': us.userprofile,
        'unenrolled': ue.userprofile,
        'students': students,
    }

def create_default_courses(users):
    from course.models import Course, CourseInstance, Enrollment

    course = Course.objects.create(
        name="Def. Course",
        code="DEF000",
        url="def",
    )
    manual_course = Course.objects.create(
        name="Aplus Manual",
        code="aplus-manual",
        url="aplus-manual",
    )
    test_course = Course.objects.create(
        name="Test Course",
        code="test-course",
        url="test-course",
    )

    today = timezone.now()
    instance = CourseInstance.objects.create(
        course=course,
        instance_name="Current",
        url="current",
        starting_time=today,
        ending_time=today + timedelta(days=365),
        configure_url="http://grader:8080/default/aplus-json",
    )
    instance.set_teachers([users['teacher']])
    instance.set_assistants([users['assistant']])

    manual_instance = CourseInstance.objects.create(
        course=manual_course,
        instance_name="Main",
        url="master",
        starting_time=today - timedelta(days=3 * 365),
        ending_time=today + timedelta(days=3 * 365),
        configure_url="http://grader:8080/aplus-manual/aplus-json",
    )
    manual_instance.set_teachers([users['teacher']])

    testcourse_instance = CourseInstance.objects.create(
        course=test_course,
        instance_name="Master",
        url="master",
        starting_time=today - timedelta(days=3 * 365),
        ending_time=today + timedelta(days=3 * 365),
        configure_url="http://grader:8080/test-course-master/aplus-json",
    )
    testcourse_instance.set_teachers([users['teacher']])

    instance.enroll_student(users['student'].user)

    for student in users['students']:
        instance.enroll_student(student.user)
        manual_instance.enroll_student(student.user)
        testcourse_instance.enroll_student(student.user)

    return {
        'default': instance,
        'aplus-manual': manual_instance,
        'test-course-master': testcourse_instance,
    }

def create_default_services():
    from external_services.models import LTIService
    from pylti1p3.contrib.django.lti1p3_tool_config.models import (
        LtiTool,
        LtiToolKey,
    )

    services = {}

    services['rubyric+'] = LTIService.objects.create(
        url="http://rubyric:8090/session/lti",
        menu_label="Rubyric+",
        menu_icon_class="save-file",
        consumer_key="foo",
        consumer_secret="bar",
    )

    services['rubyric'] = LTIService.objects.create(
        url="http://rubyric:8091/session/lti",
        menu_label="Rubyric",
        menu_icon_class="save-file",
        consumer_key="rubyric",
        consumer_secret="rubyric",
    )

    services['grader'] = LTIService.objects.create(
        url="http://grader:8080/",
        destination_region=0,
        menu_label="Grader",
        menu_icon_class="save-file",
        access_settings=5,
        consumer_key="grader",
        consumer_secret="grader",
    )

    # A+ as an LTI Tool v1.3 for Moodle as the Platform.
    with open("/srv/lti-tool-private.key", "r") as keyfile:
        lti_tool_private = keyfile.read()
    with open("/srv/lti-tool-public.key", "r") as keyfile:
        lti_tool_public = keyfile.read()

    lti_tool_key = LtiToolKey.objects.create(
        name="http://moodle:8050",
        private_key=lti_tool_private,
        public_key=lti_tool_public,
    )
    services['lti_tool'] = LtiTool.objects.create(
        title="http://moodle:8050",
        issuer="http://moodle:8050",
        client_id="abcdefghijklmn",
        use_by_default=True,
        auth_login_url="http://moodle:8050/mod/lti/auth.php",
        auth_token_url="http://moodle:8050/mod/lti/token.php",
        key_set_url="http://moodle:8050/mod/lti/certs.php",
        tool_key=lti_tool_key,
        deployment_ids='["1"]',
    )

    return services

def create_default_user_tags(course_instance, students):
    from course.models import UserTag, UserTagging

    tag_basic, created = UserTag.objects.get_or_create(
        course_instance=course_instance,
        name="Basic",
        slug="basic",
        description="Basic level",
        color="#2cff14",
    )
    tag_intermediate, created = UserTag.objects.get_or_create(
        course_instance=course_instance,
        name="Intermediate",
        slug="intermediate",
        description="Intermediate level",
        color="#e4fc2d",
    )
    tag_advanced, created = UserTag.objects.get_or_create(
        course_instance=course_instance,
        name="Advanced",
        slug="advanced",
        description="Advanced level",
        color="#f51505",
    )
    tag_highschool, created = UserTag.objects.get_or_create(
        course_instance=course_instance,
        name="High school",
        slug="highschool",
        description="High school student",
        color="#07dde8",
    )
    tag_exchange, created = UserTag.objects.get_or_create(
        course_instance=course_instance,
        name="Exchange",
        slug="exchange",
        description="Exchange student",
        color="#6706bd",
    )
    tag_local, created = UserTag.objects.get_or_create(
        course_instance=course_instance,
        name="Local",
        slug="local",
        description="Local student",
        color="#1100fc",
    )
    tag_visitor, created = UserTag.objects.get_or_create(
        course_instance=course_instance,
        name="Visitor",
        slug="visitor",
        description="Visiting student",
        color="#ff63d3",
    )

    for i, student in enumerate(students):
        if i % 3 == 0:
            UserTagging.objects.set(student, tag_basic)
        elif i % 3 == 1:
            UserTagging.objects.set(student, tag_intermediate)
        else:
            UserTagging.objects.set(student, tag_advanced)

        if i % 2 == 0:
            UserTagging.objects.set(student, tag_local)
        elif i % 7 == 0:
            UserTagging.objects.set(student, tag_highschool)
        elif i % 3 == 0:
            UserTagging.objects.set(student, tag_exchange)
        else:
            UserTagging.objects.set(student, tag_visitor)

    tags = [tag_basic, tag_intermediate, tag_advanced, tag_highschool, tag_exchange, tag_local, tag_visitor]
    return { t.slug: t for t in tags }

def create_default_student_groups(course_instance, students):
    from course.models import StudentGroup

    # Create groups. Some students don't have any group and some have more than one.
    for i in range(len(students) - 2):
        if i % 3 == 0 and i % 2 == 1:
            g = StudentGroup.objects.create(course_instance=course_instance)
            g.members.add(students[i], students[i+1], students[i+2])
        if i % 5 == 0:
            g = StudentGroup.objects.create(course_instance=course_instance)
            g.members.add(students[i], students[i+1])


if __name__ == '__main__':
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aplus.settings")
    sys.path.insert(0, '')
    django.setup()

    users = create_default_users()
    courses = create_default_courses(users)
    services = create_default_services()
    tags = create_default_user_tags(courses['default'], users['students'])
    create_default_student_groups(courses['default'], users['students'])

