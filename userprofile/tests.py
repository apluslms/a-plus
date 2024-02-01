from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from django.conf import settings

from course.models import Course, CourseInstance
from exercise.models import LearningObjectCategory
from userprofile.models import UserProfile


class UserProfileTest(TestCase):
    def setUp(self):
        # Set the user's id manually so that user.id is different than userprofile.id.
        self.student = User(
            id=101,
            username="testUser",
            first_name="Superb",
            last_name="Student",
            email="test@aplus.com"
        )
        self.student.set_password("testPassword")
        self.student.save()
        self.student_profile = self.student.userprofile
        self.student_profile.student_id = "12345X"
        self.student_profile.organization = settings.LOCAL_ORGANIZATION
        self.student_profile.save()

        self.grader = User(
            id=102,
            username="grader",
            first_name="Grumpy",
            last_name="Grader",
            email="grader@aplus.com"
        )
        self.grader.set_password("graderPassword")
        self.grader.save()
        self.grader_profile = self.grader.userprofile
        self.grader_profile.student_id = "67890Y"
        self.grader_profile.organization = settings.LOCAL_ORGANIZATION
        self.grader_profile.save()

        self.teacher = User(
            id=103,
            username="teacher",
            first_name="Tedious",
            last_name="Teacher",
            email="teacher@aplus.com"
        )
        self.teacher.set_password("teacherPassword")
        self.teacher.save()
        self.teacher_profile = self.teacher.userprofile

        self.superuser = User(
            id=104,
            username="superuser",
            first_name="Super",
            last_name="User",
            email="superuser@aplus.com",
            is_superuser=True
        )
        self.superuser.set_password("superuserPassword")
        self.superuser.save()
        self.superuser_profile = self.superuser.userprofile

        self.course = Course.objects.create(
            name="test course",
            code="123456",
            url="Course-Url"
        )

        self.today = timezone.now()
        self.tomorrow = self.today + timedelta(days=1)
        self.two_days_from_now = self.tomorrow + timedelta(days=1)

        self.course_instance1 = CourseInstance.objects.create(
            instance_name="Fall 2011 day 1",
            starting_time=self.today,
            ending_time=self.tomorrow,
            course=self.course,
            url="T-00.1000_d1"
        )
        self.course_instance1.add_teacher(self.teacher.userprofile)
        self.course_instance1.add_assistant(self.grader.userprofile)

        self.course_instance2 = CourseInstance.objects.create(
            instance_name="Fall 2011 day 2",
            starting_time=self.tomorrow,
            ending_time=self.two_days_from_now,
            course=self.course,
            url="T-00.1000_d2"
        )
        self.course_instance2.add_teacher(self.teacher.userprofile)

        self.learning_object_category1 = LearningObjectCategory.objects.create(
            name="test category 1",
            course_instance=self.course_instance1
        )
        #self.learning_object_category1.hidden_to.add(self.student_profile)
        #self.learning_object_category1.hidden_to.add(self.grader_profile)

        self.learning_object_category2 = LearningObjectCategory.objects.create(
            name="test category 2",
            course_instance=self.course_instance1
        )
        #self.learning_object_category2.hidden_to.add(self.student_profile)

        self.learning_object_category3 = LearningObjectCategory.objects.create(
            name="test category 3",
            course_instance=self.course_instance2
        )

    def test_user_id_not_equal_profile_id(self):
        self.assertEqual(self.student.id, 101)
        self.assertEqual(self.grader.id, 102)
        self.assertEqual(self.teacher.id, 103)
        self.assertEqual(self.superuser.id, 104)
        self.assertEqual(self.student_profile.id, 1)
        self.assertEqual(self.grader_profile.id, 2)
        self.assertEqual(self.teacher_profile.id, 3)
        self.assertEqual(self.superuser_profile.id, 4)

        self.assertNotEqual(self.student.id, self.student_profile.id)
        self.assertNotEqual(self.grader.id, self.grader_profile.id)
        self.assertNotEqual(self.teacher.id, self.teacher_profile.id)
        self.assertNotEqual(self.superuser.id, self.superuser_profile.id)

    def test_userprofile_get_by_student_id(self):
        self.assertEqual(self.student_profile, UserProfile.get_by_student_id("12345X"))
        self.assertEqual(self.grader_profile, UserProfile.get_by_student_id("67890Y"))
        self.assertRaises(UserProfile.DoesNotExist, UserProfile.get_by_student_id, "111111")

    def test_userprofile_unicode_string(self):
        self.assertEqual("testUser (Superb Student, test@aplus.com, 12345X)", str(self.student_profile))
        self.assertEqual("grader (Grumpy Grader, grader@aplus.com, 67890Y)", str(self.grader_profile))
        self.assertEqual("teacher (Tedious Teacher, teacher@aplus.com)", str(self.teacher_profile))
        self.assertEqual("superuser (Super User, superuser@aplus.com)", str(self.superuser_profile))

    def test_userprofile_shortname(self):
        self.assertEqual("Superb S.", self.student_profile.shortname)
        self.assertEqual("Grumpy G.", self.grader_profile.shortname)
        self.assertEqual("Tedious T.", self.teacher_profile.shortname)
        self.assertEqual("Super U.", self.superuser_profile.shortname)

#     def test_userprofile_reset_hidden_categories_cache(self):
#         self.student_profile.reset_hidden_categories_cache()
#         self.assertEqual(2, len(self.student_profile.cached_hidden_categories))
#         self.assertEqual(self.learning_object_category1, self.student_profile.cached_hidden_categories[0])
#         self.assertEqual(self.learning_object_category2, self.student_profile.cached_hidden_categories[1])
#
#         self.grader_profile.reset_hidden_categories_cache()
#         self.assertEqual(1, len(self.grader_profile.cached_hidden_categories))
#         self.assertEqual(self.learning_object_category1, self.grader_profile.cached_hidden_categories[0])
#
#         self.teacher_profile.reset_hidden_categories_cache()
#         self.assertEqual(0, len(self.teacher_profile.cached_hidden_categories))
#
#         self.superuser_profile.reset_hidden_categories_cache()
#         self.assertEqual(0, len(self.superuser_profile.cached_hidden_categories))
#
#
#     def test_userprofile_hidden_categories_cache(self):
#         student_hidden_categories_cache = self.student_profile.get_hidden_categories_cache()
#         self.assertEqual(2, len(student_hidden_categories_cache))
#         self.assertEqual(self.learning_object_category1, student_hidden_categories_cache[0])
#         self.assertEqual(self.learning_object_category2, student_hidden_categories_cache[1])
#
#         grader_hidden_categories_cache = self.grader_profile.get_hidden_categories_cache()
#         self.assertEqual(1, len(grader_hidden_categories_cache))
#         self.assertEqual(self.learning_object_category1, grader_hidden_categories_cache[0])
#
#         self.assertEqual(0, len(self.teacher_profile.get_hidden_categories_cache()))
#
#         self.assertEqual(0, len(self.superuser_profile.get_hidden_categories_cache()))

#     def test_studentgroup_students_from_request(self):
#         requestWithGroup = HttpRequest()
#         requestWithGroup.user = self.student
#         requestWithGroup.META["STUDENT_GROUP"] = self.student_group2
#         studentsFromRequestWithGroup = StudentGroup.get_students_from_request(requestWithGroup)
#         self.assertEqual(2, len(studentsFromRequestWithGroup))
#         self.assertEqual(self.student_profile, studentsFromRequestWithGroup[0])
#         self.assertEqual(self.grader_profile, studentsFromRequestWithGroup[1])
#
#         requestWithoutGroup = HttpRequest()
#         requestWithoutGroup.user = self.student
#         studentsFromRequestWithoutGroup = StudentGroup.get_students_from_request(requestWithoutGroup)
#         self.assertEqual(1, len(studentsFromRequestWithoutGroup))
#         self.assertEqual(self.student_profile, studentsFromRequestWithoutGroup[0])
