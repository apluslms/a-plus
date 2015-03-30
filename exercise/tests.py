# Django
from django.test import TestCase
from django.test.client import Client

# Aalto+
from exercise.exercise_models import *
from exercise.submission_models import *
from userprofile.models import *

# Python
from datetime import datetime, timedelta

class ExerciseTest(TestCase):
    def setUp(self):
        self.client = Client()

        self.user = User(username="testUser")
        self.user.set_password("testPassword")
        self.user.save()

        self.grader = User(username="grader")
        self.grader.set_password("graderPassword")
        self.grader.save()

        self.staff_member = User(username="staff", is_staff=True)
        self.staff_member.set_password("staffPassword")
        self.staff_member.save()

        self.course = Course.objects.create(
            name="test course",
            code="123456",
            url="Course-Url"
        )

        self.today = datetime.now()
        self.yesterday = self.today - timedelta(days=1)
        self.tomorrow = self.today + timedelta(days=1)
        self.two_days_from_now = self.tomorrow + timedelta(days=1)
        self.three_days_from_now = self.two_days_from_now + timedelta(days=1)

        self.course_instance = CourseInstance.objects.create(
            instance_name="Fall 2011 day 1",
            website="http://www.example.com",
            starting_time=self.today,
            ending_time=self.tomorrow,
            course=self.course,
            url="T-00.1000_d1"
        )

        self.course_module = CourseModule.objects.create(
            name="test module",
            points_to_pass=15,
            course_instance=self.course_instance,
            opening_time=self.today,
            closing_time=self.tomorrow
        )

        self.course_module_with_late_submissions_allowed = CourseModule.objects.create(
            name="test module",
            points_to_pass=50,
            course_instance=self.course_instance,
            opening_time=self.today,
            closing_time=self.tomorrow,
            late_submissions_allowed=True,
            late_submission_deadline=self.two_days_from_now,
            late_submission_penalty=0.2
        )

        self.learning_object_category = LearningObjectCategory.objects.create(
            name="test category",
            course_instance=self.course_instance,
            points_to_pass=5
        )

        self.hidden_learning_object_category = LearningObjectCategory.objects.create(
            name="hidden category",
            course_instance=self.course_instance
        )
        self.hidden_learning_object_category.hidden_to.add(self.user.get_profile())

        self.base_exercise = BaseExercise.objects.create(
            name="test exercise",
            course_module=self.course_module,
            category=self.learning_object_category
        )

        self.base_exercise2 = BaseExercise.objects.create(
            name="test exercise 2",
            course_module=self.course_module,
            category=self.learning_object_category,
            max_points=50
        )

        self.base_exercise_with_late_submission_allowed = BaseExercise.objects.create(
            name="test exercise with late submissions allowed",
            course_module=self.course_module_with_late_submissions_allowed,
            category=self.learning_object_category
        )

        self.submission = Submission.objects.create(
            exercise=self.base_exercise,
            grader=self.grader.get_profile()
        )
        self.submission.submitters.add(self.user.get_profile())

        self.late_submission = Submission.objects.create(
            exercise=self.base_exercise,
            grader=self.grader.get_profile(),
            submission_time=self.two_days_from_now
        )
        self.late_submission.submitters.add(self.user.get_profile())

        self.submission_when_late_allowed = Submission.objects.create(
            exercise=self.base_exercise_with_late_submission_allowed,
            grader=self.grader.get_profile()
        )
        self.submission_when_late_allowed.submitters.add(self.user.get_profile())

        self.late_submission_when_late_allowed = Submission.objects.create(
            exercise=self.base_exercise_with_late_submission_allowed,
            grader=self.grader.get_profile(),
            submission_time=self.two_days_from_now
        )
        self.late_submission_when_late_allowed.submitters.add(self.user.get_profile())

        self.late_late_submission_when_late_allowed = Submission.objects.create(
            exercise=self.base_exercise_with_late_submission_allowed,
            grader=self.grader.get_profile(),
            submission_time=self.three_days_from_now
        )
        self.late_late_submission_when_late_allowed.submitters.add(self.user.get_profile())

        self.course_hook = CourseHook.objects.create(
            hook_url="test_hook_url",
            course_instance=self.course_instance
        )

    def test_course_module_exercises_list(self):
        exercises = self.course_module.get_exercises()
        exercises_with_late_submission_allowed = self.course_module_with_late_submissions_allowed.get_exercises()
        self.assertEquals(2, len(exercises))
        self.assertEquals("test exercise", exercises[0].name)
        self.assertEquals("test exercise 2", exercises[1].name)
        self.assertEquals(1, len(exercises_with_late_submission_allowed))
        self.assertEquals("test exercise with late submissions allowed", exercises_with_late_submission_allowed[0].name)

    def test_course_module_maximum_points(self):
        self.assertEquals(150, self.course_module.get_maximum_points())
        self.assertEquals(100, self.course_module_with_late_submissions_allowed.get_maximum_points())

    def test_course_module_required_percentage(self):
        self.assertEquals(10, self.course_module.get_required_percentage())
        self.assertEquals(50, self.course_module_with_late_submissions_allowed.get_required_percentage())

    def test_course_module_late_submission_point_worth(self):
        self.assertEquals(100, self.course_module.get_late_submission_point_worth())
        self.assertEquals(80, self.course_module_with_late_submissions_allowed.get_late_submission_point_worth())

    def test_course_module_open(self):
        self.assertFalse(self.course_module.is_open(self.yesterday))
        self.assertTrue(self.course_module.is_open(self.today))
        self.assertTrue(self.course_module.is_open())
        self.assertTrue(self.course_module.is_open(self.tomorrow))
        self.assertFalse(self.course_module.is_open(self.two_days_from_now))

    def test_course_module_expired(self):
        self.assertFalse(self.course_module.is_expired(self.yesterday))
        self.assertFalse(self.course_module.is_expired(self.today))
        self.assertFalse(self.course_module.is_expired())
        self.assertFalse(self.course_module.is_expired(self.tomorrow))
        self.assertTrue(self.course_module.is_expired(self.two_days_from_now))

    def test_course_module_after_open(self):
        self.assertFalse(self.course_module.is_expired(self.yesterday))
        self.assertFalse(self.course_module.is_expired(self.today))
        self.assertFalse(self.course_module.is_expired())
        self.assertFalse(self.course_module.is_expired(self.tomorrow))
        self.assertTrue(self.course_module.is_expired(self.two_days_from_now))

    def test_course_module_breadcrumb(self):
        breadcrumb = self.course_module.get_breadcrumb()
        self.assertEqual(2, len(breadcrumb))
        self.assertEqual(2, len(breadcrumb[0]))
        self.assertEqual(2, len(breadcrumb[1]))
        self.assertEqual("123456 test course", breadcrumb[0][0])
        self.assertEqual("/course/Course-Url/", breadcrumb[0][1])
        self.assertEqual("Fall 2011 day 1", breadcrumb[1][0])
        self.assertEqual("/course/Course-Url/T-00.1000_d1/", breadcrumb[1][1])

    def test_learning_object_category_unicode_string(self):
        self.assertEqual("test category -- 123456: Fall 2011 day 1", str(self.learning_object_category))
        self.assertEqual("hidden category -- 123456: Fall 2011 day 1", str(self.hidden_learning_object_category))

    def test_learning_object_category_exercises(self):
        self.assertEquals(3, len(self.learning_object_category.get_exercises()))
        self.assertEquals(0, len(self.hidden_learning_object_category.get_exercises()))

    def test_learning_object_category_max_points(self):
        self.assertEquals(250, self.learning_object_category.get_maximum_points())
        self.assertEquals(0, self.hidden_learning_object_category.get_maximum_points())

    def test_learning_object_category_required_percentage(self):
        self.assertEquals(2, self.learning_object_category.get_required_percentage())
        self.assertEquals(0, self.hidden_learning_object_category.get_required_percentage())

    def test_learning_object_category_hiding(self):
        self.assertFalse(self.learning_object_category.is_hidden_to(self.user.get_profile()))
        self.assertFalse(self.learning_object_category.is_hidden_to(self.grader.get_profile()))
        self.assertTrue(self.hidden_learning_object_category.is_hidden_to(self.user.get_profile()))
        self.assertFalse(self.hidden_learning_object_category.is_hidden_to(self.grader.get_profile()))

        self.hidden_learning_object_category.set_hidden_to(self.user.get_profile(), False)
        self.hidden_learning_object_category.set_hidden_to(self.grader.get_profile())

        self.assertFalse(self.hidden_learning_object_category.is_hidden_to(self.user.get_profile()))
        self.assertTrue(self.hidden_learning_object_category.is_hidden_to(self.grader.get_profile()))

        self.hidden_learning_object_category.set_hidden_to(self.user.get_profile(), True)
        self.hidden_learning_object_category.set_hidden_to(self.grader.get_profile(), False)

        self.assertTrue(self.hidden_learning_object_category.is_hidden_to(self.user.get_profile()))
        self.assertFalse(self.hidden_learning_object_category.is_hidden_to(self.grader.get_profile()))