from django.test import TestCase
from django.http import HttpRequest

from userprofile.models import *
from notification.models import *
from exercise.exercise_models import *

from datetime import datetime, timedelta

class UserProfileTest(TestCase):
    def setUp(self):
        self.student = User(username="testUser", first_name="Superb", last_name="Student", email="test@aplus.com")
        self.student.set_password("testPassword")
        self.student.save()
        self.student_profile = self.student.get_profile()
        self.student_profile.student_id = "12345X"
        self.student_profile.save()

        self.grader = User(username="grader", first_name="Grumpy", last_name="Grader", email="grader@aplus.com")
        self.grader.set_password("graderPassword")
        self.grader.save()
        self.grader_profile = self.grader.get_profile()
        self.grader_profile.student_id = "67890Y"
        self.grader_profile.save()

        self.teacher = User(username="teacher", first_name="Tedious", last_name="Teacher", email="teacher@aplus.com", is_staff=True)
        self.teacher.set_password("teacherPassword")
        self.teacher.save()
        self.teacher_profile = self.teacher.get_profile()

        self.superuser = User(username="superuser", first_name="Super", last_name="User", email="superuser@aplus.com", is_superuser=True)
        self.superuser.set_password("superuserPassword")
        self.superuser.save()
        self.superuser_profile = self.superuser.get_profile()

        self.student_group1 = StudentGroup.objects.create(
            name="group1",
            description="testGroup1",
            member_limit=1,
            is_public=False
        )
        self.student_group1.members.add(self.student_profile)

        self.student_group2 = StudentGroup.objects.create(
            name="group2",
            description="testGroup2",
            member_limit=3,
            is_public=False
        )
        self.student_group2.members.add(self.student_profile)
        self.student_group2.members.add(self.grader_profile)

        self.student_group3 = StudentGroup.objects.create(
            name="group3",
            description="testGroup3",
            member_limit=3,
            is_public=False
        )
        self.student_group3.members.add(self.student_profile)
        self.student_group3.members.add(self.grader_profile)

        self.course = Course.objects.create(
            name="test course",
            code="123456",
            url="Course-Url"
        )
        self.course.teachers.add(self.teacher.get_profile())

        self.today = datetime.now()
        self.tomorrow = self.today + timedelta(days=1)
        self.two_days_from_now = self.tomorrow + timedelta(days=1)

        self.course_instance1 = CourseInstance.objects.create(
            instance_name="Fall 2011 day 1",
            website="http://www.example.com",
            starting_time=self.today,
            ending_time=self.tomorrow,
            course=self.course,
            url="T-00.1000_d1"
        )
        self.course_instance1.assistants.add(self.grader.get_profile())

        self.course_instance2 = CourseInstance.objects.create(
            instance_name="Fall 2011 day 2",
            website="http://www.example.com",
            starting_time=self.tomorrow,
            ending_time=self.two_days_from_now,
            course=self.course,
            url="T-00.1000_d2"
        )

        self.notification1 = Notification.objects.create(
            subject="test1",
            notification="testNotification1",
            sender=self.superuser_profile,
            recipient=self.student_profile,
            course_instance=self.course_instance1
        )

        self.notification2 = Notification.objects.create(
            subject="test2",
            notification="testNotification2",
            sender=self.superuser_profile,
            recipient=self.grader_profile,
            course_instance=self.course_instance1
        )

        self.notification3 = Notification.objects.create(
            subject="test3",
            notification="testNotification3",
            sender=self.superuser_profile,
            recipient=self.student_profile,
            course_instance=self.course_instance2
        )

        self.notification4 = Notification.objects.create(
            subject="test4",
            notification="testNotification4",
            sender=self.superuser_profile,
            recipient=self.grader_profile,
            course_instance=self.course_instance1
        )

        self.notification5 = Notification.objects.create(
            subject="test5",
            notification="testNotification5",
            sender=self.superuser_profile,
            recipient=self.student_profile,
            course_instance=self.course_instance2
        )

        self.learning_object_category1 = LearningObjectCategory.objects.create(
            name="test category 1",
            course_instance=self.course_instance1
        )
        self.learning_object_category1.hidden_to.add(self.student_profile)
        self.learning_object_category1.hidden_to.add(self.grader_profile)

        self.learning_object_category2 = LearningObjectCategory.objects.create(
            name="test category 2",
            course_instance=self.course_instance1
        )
        self.learning_object_category2.hidden_to.add(self.student_profile)

        self.learning_object_category3 = LearningObjectCategory.objects.create(
            name="test category 3",
            course_instance=self.course_instance2
        )

    def test_userprofile_get_by_student_id(self):
        self.assertEqual(self.student_profile, UserProfile.get_by_student_id("12345X"))
        self.assertEqual(self.grader_profile, UserProfile.get_by_student_id("67890Y"))
        self.assertRaises(UserProfile.DoesNotExist, UserProfile.get_by_student_id, "111111")

    def test_userprofile_unicode_string(self):
        self.assertEqual("testUser", str(self.student_profile))
        self.assertEqual("grader", str(self.grader_profile))
        self.assertEqual("teacher", str(self.teacher_profile))
        self.assertEqual("superuser", str(self.superuser_profile))

    def test_userprofile_gravatar_url(self):
        self.assertEqual("http://www.gravatar.com/avatar/36eb57f675f34b81bd859c525cb2b676?d=identicon", self.student_profile._generate_gravatar_url())
        self.assertEqual("http://www.gravatar.com/avatar/e2321e37326539393fbae72b7558df8e?d=identicon", self.grader_profile._generate_gravatar_url())
        self.assertEqual("http://www.gravatar.com/avatar/1bfe4ecc42454c9c1dc02bf93073a414?d=identicon", self.teacher_profile._generate_gravatar_url())
        self.assertEqual("http://www.gravatar.com/avatar/f35e575136edbfb920643d10560e8814?d=identicon", self.superuser_profile._generate_gravatar_url())

    def test_userprofile_shortname(self):
        self.assertEqual("Superb S.", self.student_profile.get_shortname())
        self.assertEqual("Grumpy G.", self.grader_profile.get_shortname())
        self.assertEqual("Tedious T.", self.teacher_profile.get_shortname())
        self.assertEqual("Super U.", self.superuser_profile.get_shortname())

    def test_userprofile_courseinstance_staff_queryset(self):
        student_staff_courseinstances = self.student_profile.get_courseinstance_staff_queryset()
        self.assertEqual(0, len(student_staff_courseinstances))
        grader_staff_courseinstances = self.grader_profile.get_courseinstance_staff_queryset()
        self.assertEqual(1, len(grader_staff_courseinstances))
        self.assertEqual(self.course_instance1, grader_staff_courseinstances[0])
        teacher_staff_courseinstances = self.teacher_profile.get_courseinstance_staff_queryset()
        self.assertEqual(2, len(teacher_staff_courseinstances))
        self.assertEqual(self.course_instance1, teacher_staff_courseinstances[0])
        self.assertEqual(self.course_instance2, teacher_staff_courseinstances[1])

    def test_userprofile_is_staff(self):
        self.assertFalse(self.student_profile.is_staff())
        self.assertFalse(self.grader_profile.is_staff())
        self.assertTrue(self.teacher_profile.is_staff())
        self.assertTrue(self.superuser_profile.is_staff())

    def test_userprofile_unread_notification_count(self):
        self.assertEqual(3, self.student_profile.get_unread_notification_count())
        self.assertEqual(2, self.grader_profile.get_unread_notification_count())
        self.assertEqual(0, self.teacher_profile.get_unread_notification_count())
        self.assertEqual(0, self.superuser_profile.get_unread_notification_count())

    def test_userprofile_unread_notification_course_instances(self):
        self.assertEqual(2, len(self.student_profile.get_unread_notification_course_instances()))
        self.assertEqual(1, len(self.grader_profile.get_unread_notification_course_instances()))
        self.assertEqual(0, len(self.teacher_profile.get_unread_notification_course_instances()))
        self.assertEqual(0, len(self.superuser_profile.get_unread_notification_course_instances()))

    def test_userprofile_reset_hidden_categories_cache(self):
        self.student_profile.reset_hidden_categories_cache()
        self.assertEqual(2, len(self.student_profile.cached_hidden_categories))
        self.assertEqual(self.learning_object_category1, self.student_profile.cached_hidden_categories[0])
        self.assertEqual(self.learning_object_category2, self.student_profile.cached_hidden_categories[1])

        self.grader_profile.reset_hidden_categories_cache()
        self.assertEqual(1, len(self.grader_profile.cached_hidden_categories))
        self.assertEqual(self.learning_object_category1, self.grader_profile.cached_hidden_categories[0])

        self.teacher_profile.reset_hidden_categories_cache()
        self.assertEqual(0, len(self.teacher_profile.cached_hidden_categories))

        self.superuser_profile.reset_hidden_categories_cache()
        self.assertEqual(0, len(self.superuser_profile.cached_hidden_categories))


    def test_userprofile_hidden_categories_cache(self):
        student_hidden_categories_cache = self.student_profile.get_hidden_categories_cache()
        self.assertEqual(2, len(student_hidden_categories_cache))
        self.assertEqual(self.learning_object_category1, student_hidden_categories_cache[0])
        self.assertEqual(self.learning_object_category2, student_hidden_categories_cache[1])

        grader_hidden_categories_cache = self.grader_profile.get_hidden_categories_cache()
        self.assertEqual(1, len(grader_hidden_categories_cache))
        self.assertEqual(self.learning_object_category1, grader_hidden_categories_cache[0])

        self.assertEqual(0, len(self.teacher_profile.get_hidden_categories_cache()))

        self.assertEqual(0, len(self.superuser_profile.get_hidden_categories_cache()))

    def test_studentgroup_names(self):
        self.assertEqual("group1", str(self.student_group1))
        self.assertEqual("group2", str(self.student_group2))
        self.assertEqual("group3", str(self.student_group3))

    def test_studentgroup_names(self):
        self.assertEqual("Superb S.", self.student_group1.get_names())
        self.assertEqual("Superb S., Grumpy G.", self.student_group2.get_names())
        self.assertEqual("Superb S., Grumpy G.", self.student_group3.get_names())

    def test_studentgroup_has_space_left(self):
        self.assertFalse(self.student_group1.has_space_left())
        self.assertTrue(self.student_group2.has_space_left())
        self.assertTrue(self.student_group3.has_space_left())

    def test_studentgroup_add_member(self):
        self.assertEqual(1, len(self.student_group1.members.all()))
        self.assertFalse(self.student_group1.add_member(self.teacher_profile))
        self.assertEqual(1, len(self.student_group1.members.all()))

        self.assertEqual(2, len(self.student_group2.members.all()))
        self.assertTrue(self.student_group2.add_member(self.teacher_profile))
        self.assertEqual(3, len(self.student_group2.members.all()))

        self.assertEqual(2, len(self.student_group3.members.all()))
        self.assertTrue(self.student_group3.add_member(self.student_profile))
        self.assertEqual(2, len(self.student_group3.members.all()))

    def test_studentgroup_students_from_request(self):
        requestWithGroup = HttpRequest()
        requestWithGroup.user = self.student
        requestWithGroup.META["STUDENT_GROUP"] = self.student_group2
        studentsFromRequestWithGroup = StudentGroup.get_students_from_request(requestWithGroup)
        self.assertEqual(2, len(studentsFromRequestWithGroup))
        self.assertEqual(self.student_profile, studentsFromRequestWithGroup[0])
        self.assertEqual(self.grader_profile, studentsFromRequestWithGroup[1])

        requestWithoutGroup = HttpRequest()
        requestWithoutGroup.user = self.student
        studentsFromRequestWithoutGroup = StudentGroup.get_students_from_request(requestWithoutGroup)
        self.assertEqual(1, len(studentsFromRequestWithoutGroup))
        self.assertEqual(self.student_profile, studentsFromRequestWithoutGroup[0])
