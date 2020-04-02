from datetime import timedelta

from django.test import TestCase
from django.test.client import Client
from django.utils import timezone
from django.urls import reverse

from course.models import Course, CourseInstance, CourseModule, \
    LearningObjectCategory
from deviations.models import DeadlineRuleDeviation
from exercise.exercise_models import ExerciseWithAttachment
from userprofile.models import User


class DeviationsTest(TestCase):
    def setUp(self):
        self.client = Client()

        self.user = User(username="testUser", first_name="First", last_name="Last")
        self.user.set_password("testPassword")
        self.user.save()

        self.user1 = User(username="testUser1")
        self.user1.set_password("testPassword")
        self.user1.save()

        self.user2 = User(username="testUser2")
        self.user2.set_password("testPassword")
        self.user2.save()

        self.superuser = User(username="staff", is_staff=False, is_superuser=True)
        self.superuser.set_password("staffPassword")
        self.superuser.save()

        self.course = Course.objects.create(
            name="test course",
            code="123456",
            url="Course-Url"
        )

        self.today = timezone.now()
        self.tomorrow = self.today + timedelta(days=1)
        self.two_days_from_now = self.today + timedelta(days=2)

        self.course_instance = CourseInstance.objects.create(
            instance_name="Fall 2011 day 1",
            starting_time=self.today,
            ending_time=self.tomorrow,
            course=self.course,
            url="T-00.1000_d1"
        )

        self.course_instance.enroll_student(self.user)

        self.course_module = CourseModule.objects.create(
            name="test module",
            url="test-module",
            points_to_pass=15,
            course_instance=self.course_instance,
            opening_time=self.today,
            closing_time=self.tomorrow
        )

        self.learning_object_category = LearningObjectCategory.objects.create(
            name="test category",
            course_instance=self.course_instance,
            points_to_pass=5
        )

        self.exercise_with_attachment = ExerciseWithAttachment.objects.create(
            name="test exercise 3",
            course_module=self.course_module,
            category=self.learning_object_category,
            max_points=50,
            points_to_pass=50,
            max_submissions=0,
            files_to_submit="test1.txt|test2.txt|img.png",
            content="test_instructions",
            url="test_exercise"
        )

        self.deadline_rule_deviation = DeadlineRuleDeviation.objects.create(
            exercise=self.exercise_with_attachment,
            submitter=self.user.userprofile,
            extra_minutes=1440  # One day
        )

    def test_deadline_rule_deviation_extra_time(self):
        self.assertEqual(timedelta(days=1), self.deadline_rule_deviation.get_extra_time())

    def test_deadline_rule_deviation_new_deadline(self):
        self.assertEqual(self.two_days_from_now, self.deadline_rule_deviation.get_new_deadline())

    def test_deadline_rule_deviation_normal_deadline(self):
        self.assertEqual(self.tomorrow, self.deadline_rule_deviation.get_normal_deadline())

    def test_add_multiple_dl_deviations(self):
        self.client.login(username="staff", password="staffPassword")
        self.course_instance.enroll_student(self.user1)
        self.course_instance.enroll_student(self.user2)
        self.assertIsNone(self.exercise_with_attachment.one_has_deadline_deviation([self.user1.userprofile]))
        self.assertIsNone(self.exercise_with_attachment.one_has_deadline_deviation([self.user2.userprofile]))
        response =self.client.post(
            reverse("deviations-add-dl", kwargs={
                'course_slug': self.course.url,
                'instance_slug': self.course_instance.url,
            }),
            # TODO: When deviation forms start to use ajax-search, these should
            # be user id's instead of userprofiles.
            {'submitter': [self.user1.id, self.user2.id],
            'exercise': [self.exercise_with_attachment],
            'minutes': 10,
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(DeadlineRuleDeviation.objects.get(submitter=self.user1.userprofile, exercise=self.exercise_with_attachment))
        self.assertIsNotNone(self.exercise_with_attachment.one_has_deadline_deviation([self.user2.userprofile]))
