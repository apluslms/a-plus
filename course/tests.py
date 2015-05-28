from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.test import TestCase
from django.test.client import Client

from course.models import Course, CourseInstance, CourseHook, \
    get_visible_open_course_instances
from exercise.models import CourseModule, LearningObjectCategory, \
    BaseExercise, Submission


class CourseTest(TestCase):
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

        today = datetime.now()
        tomorrow = today + timedelta(days=1)
        after_tomorrow = tomorrow + timedelta(days=1)
        yesterday = today - timedelta(days=1)

        self.past_course_instance = CourseInstance.objects.create(
            instance_name="Fall 2011 day 0",
            website="http://www.example.com",
            starting_time=yesterday,
            ending_time=today,
            course=self.course,
            url="T-00.1000_d0"
        )

        self.current_course_instance = CourseInstance.objects.create(
            instance_name="Fall 2011 day 1",
            website="http://www.example.com",
            starting_time=today,
            ending_time=tomorrow,
            course=self.course,
            url="T-00.1000_d1"
        )

        self.future_course_instance = CourseInstance.objects.create(
            instance_name="Fall 2011 day 2",
            website="http://www.example.com",
            starting_time=tomorrow,
            ending_time=after_tomorrow,
            course=self.course,
            url="T-00.1000_d2"
        )

        self.hidden_course_instance = CourseInstance.objects.create(
            instance_name="Secret super course",
            website="http://www.secret.com",
            starting_time=tomorrow,
            ending_time=after_tomorrow,
            course=self.course,
            url="T-00.1000_hidden",
            visible_to_students=False
        )

        self.course_module = CourseModule.objects.create(
            name="test module",
            points_to_pass=10,
            course_instance=self.current_course_instance,
            opening_time=today,
            closing_time=tomorrow
        )

        self.learning_object_category = LearningObjectCategory.objects.create(
            name="test category",
            course_instance=self.current_course_instance
        )

        self.base_exercise = BaseExercise.objects.create(
            name="test exercise",
            course_module=self.course_module,
            category=self.learning_object_category
        )

        self.submission = Submission.objects.create(
            exercise=self.base_exercise,
            grader=self.grader.userprofile
        )
        self.submission.submitters.add(self.user.userprofile)

        self.course_hook = CourseHook.objects.create(
            hook_url="test_hook_url",
            course_instance=self.current_course_instance
        )

    def test_course_instance_open(self):
        self.assertFalse(self.past_course_instance.is_open())
        self.assertTrue(self.current_course_instance.is_open())
        self.assertFalse(self.future_course_instance.is_open())

    def test_course_url(self):
        self.assertEqual("/course/Course-Url/", self.course.get_absolute_url())
        self.assertEqual("/course/Course-Url/T-00.1000_d1/", self.current_course_instance.get_absolute_url())
        self.assertEqual("/course/Course-Url/T-00.1000_hidden/", self.hidden_course_instance.get_absolute_url())

    def test_course_instance_results_url(self):
        self.assertEqual("/course/Course-Url/T-00.1000_d1/results/", self.current_course_instance.get_results_url())
        self.assertEqual("/course/Course-Url/T-00.1000_hidden/results/", self.hidden_course_instance.get_results_url())

    def test_course_staff(self):
        self.assertFalse(self.course.is_teacher(self.user.userprofile))
        self.assertFalse(self.current_course_instance.is_assistant(self.user.userprofile))
        self.assertFalse(self.current_course_instance.is_teacher(self.user.userprofile))
        self.assertFalse(self.current_course_instance.is_staff(self.user.userprofile))
        self.assertEquals(0, len(self.current_course_instance.get_course_staff()))

        self.current_course_instance.add_assistant(self.user)

        self.assertFalse(self.course.is_teacher(self.user.userprofile))
        self.assertTrue(self.current_course_instance.is_assistant(self.user.userprofile))
        self.assertFalse(self.current_course_instance.is_teacher(self.user.userprofile))
        self.assertTrue(self.current_course_instance.is_staff(self.user.userprofile))
        self.assertEquals(1, len(self.current_course_instance.get_course_staff()))

        self.course.add_teacher(self.user.userprofile)

        self.assertTrue(self.course.is_teacher(self.user.userprofile))
        self.assertTrue(self.current_course_instance.is_assistant(self.user.userprofile))
        self.assertTrue(self.current_course_instance.is_teacher(self.user.userprofile))
        self.assertTrue(self.current_course_instance.is_staff(self.user.userprofile))
        self.assertEquals(1, len(self.current_course_instance.get_course_staff()))
        self.assertEquals("testUser", self.current_course_instance.get_course_staff()[0].get_shortname())

        self.current_course_instance.assistants.clear()

        self.assertTrue(self.course.is_teacher(self.user.userprofile))
        self.assertFalse(self.current_course_instance.is_assistant(self.user.userprofile))
        self.assertTrue(self.current_course_instance.is_teacher(self.user.userprofile))
        self.assertTrue(self.current_course_instance.is_staff(self.user.userprofile))
        self.assertEquals(1, len(self.current_course_instance.get_course_staff()))

        self.course.teachers.clear()

        self.assertFalse(self.course.is_teacher(self.user.userprofile))
        self.assertFalse(self.current_course_instance.is_assistant(self.user.userprofile))
        self.assertFalse(self.current_course_instance.is_teacher(self.user.userprofile))
        self.assertFalse(self.current_course_instance.is_staff(self.user.userprofile))
        self.assertEquals(0, len(self.current_course_instance.get_course_staff()))

    def test_course_instance_visible_open(self):
        self.assertFalse(self.past_course_instance in self.course.get_visible_open_instances(self.user.userprofile))
        self.assertTrue(self.current_course_instance in self.course.get_visible_open_instances(self.user.userprofile))
        self.assertTrue(self.future_course_instance in self.course.get_visible_open_instances(self.user.userprofile))

    def test_course_breadcrumb(self):
        breadcrumb = self.course.get_breadcrumb()
        self.assertEqual(1, len(breadcrumb))
        self.assertEqual(2, len(breadcrumb[0]))
        self.assertEqual("123456 test course", breadcrumb[0][0])
        self.assertEqual("/course/Course-Url/", breadcrumb[0][1])

    def test_course_instance_breadcrumb(self):
        breadcrumb = self.current_course_instance.get_breadcrumb()
        self.assertEqual(2, len(breadcrumb))
        self.assertEqual(2, len(breadcrumb[0]))
        self.assertEqual(2, len(breadcrumb[1]))
        self.assertEqual("123456 test course", breadcrumb[0][0])
        self.assertEqual("/course/Course-Url/", breadcrumb[0][1])
        self.assertEqual("Fall 2011 day 1", breadcrumb[1][0])
        self.assertEqual("/course/Course-Url/T-00.1000_d1/", breadcrumb[1][1])

    def test_course_views(self):
        # Test viewing a course without logging in
        response = self.client.get(self.course.get_absolute_url())
        self.assertEqual(302, response.status_code)

        response = self.client.get(self.current_course_instance.get_absolute_url())
        self.assertEqual(302, response.status_code)

        self.client.login(username="testUser", password="testPassword")

        response = self.client.get(self.course.get_absolute_url())
        self.assertEqual(200, response.status_code)

        response = self.client.get(self.current_course_instance.get_absolute_url())
        self.assertEqual(200, response.status_code)

    def test_course_instance_students(self):
        students = self.current_course_instance.get_students()
        self.assertEquals(1, len(students))
        self.assertEquals("testUser", students[0].get_shortname())

        submission2 = Submission.objects.create(
            exercise=self.base_exercise,
            grader=self.grader.userprofile)
        submission2.submitters.add(self.user.userprofile)

        students = self.current_course_instance.get_students()
        self.assertEquals(1, len(students))
        self.assertEquals("testUser", students[0].get_shortname())

        submission3 = Submission.objects.create(
            exercise=self.base_exercise,
            grader=self.user.userprofile)
        submission3.submitters.add(self.grader.userprofile)

        students = self.current_course_instance.get_students()
        self.assertEquals(2, len(students))
        self.assertEquals("testUser", students[0].get_shortname())
        self.assertEquals("grader", students[1].get_shortname())

    def test_course_instance_visibility(self):
        self.assertTrue(self.current_course_instance.is_visible_to())
        self.assertFalse(self.hidden_course_instance.is_visible_to())
        self.assertTrue(self.current_course_instance.is_visible_to(self.user.userprofile))
        self.assertFalse(self.hidden_course_instance.is_visible_to(self.user.userprofile))
        self.assertTrue(self.current_course_instance.is_visible_to(self.staff_member.userprofile))
        self.assertTrue(self.hidden_course_instance.is_visible_to(self.staff_member.userprofile))

    def test_course_instance_label(self):
        self.assertEquals("Dashboard", self.current_course_instance.get_label())

    def test_course_instance_visible_open_list(self):
        open_course_instances = get_visible_open_course_instances()
        self.assertEqual(2, len(open_course_instances))
        self.assertTrue(self.current_course_instance in open_course_instances)
        self.assertTrue(self.future_course_instance in open_course_instances)

        open_course_instances = get_visible_open_course_instances(self.user.userprofile)
        self.assertEqual(2, len(open_course_instances))
        self.assertTrue(self.current_course_instance in open_course_instances)
        self.assertTrue(self.future_course_instance in open_course_instances)

        open_course_instances = get_visible_open_course_instances(self.staff_member.userprofile)
        self.assertEqual(3, len(open_course_instances))
        self.assertTrue(self.current_course_instance in open_course_instances)
        self.assertTrue(self.future_course_instance in open_course_instances)
        self.assertTrue(self.hidden_course_instance in open_course_instances)

    def test_course_instance_unicode_string(self):
        self.assertEquals("123456: Fall 2011 day 1", str(self.current_course_instance))
        self.assertEquals("123456: Secret super course", str(self.hidden_course_instance))

    def test_course_hook_unicode_string(self):
        self.assertEquals("123456: Fall 2011 day 1 -> test_hook_url", str(self.course_hook))
