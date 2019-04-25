from datetime import timedelta

from django.contrib.auth.models import User
from django.urls import reverse
from django.test import TestCase
from django.test.client import Client
from django.utils import timezone

from course.models import Course, CourseInstance, CourseHook, CourseModule, \
    LearningObjectCategory, StudentGroup
from exercise.models import BaseExercise, Submission
from exercise.exercise_models import LearningObject


class CourseTest(TestCase):
    def setUp(self):
        self.client = Client()

        self.user = User(username="testUser")
        self.user.set_password("testPassword")
        self.user.save()

        self.grader = User(username="grader", is_staff=True)
        self.grader.set_password("graderPassword")
        self.grader.save()

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
        self.two_days_from_now = self.tomorrow + timedelta(days=1)
        self.yesterday = self.today - timedelta(days=1)

        self.past_course_instance = CourseInstance.objects.create(
            instance_name="Fall 2011 day 0",
            starting_time=self.yesterday,
            ending_time=self.today,
            course=self.course,
            url="T-00.1000_d0"
        )

        self.current_course_instance = CourseInstance.objects.create(
            instance_name="Fall 2011 day 1",
            starting_time=self.today,
            ending_time=self.tomorrow,
            course=self.course,
            url="T-00.1000_d1"
        )

        self.future_course_instance = CourseInstance.objects.create(
            instance_name="Fall 2011 day 2",
            starting_time=self.tomorrow,
            ending_time=self.two_days_from_now,
            course=self.course,
            url="T-00.1000_d2"
        )

        self.hidden_course_instance = CourseInstance.objects.create(
            instance_name="Secret super course",
            starting_time=self.tomorrow,
            ending_time=self.two_days_from_now,
            course=self.course,
            url="T-00.1000_hidden",
            visible_to_students=False
        )

        self.course_module = CourseModule.objects.create(
            name="test module",
            url="test-module",
            points_to_pass=10,
            course_instance=self.current_course_instance,
            opening_time=self.today,
            closing_time=self.tomorrow
        )

        self.course_module_with_late_submissions_allowed = CourseModule.objects.create(
            name="test module",
            url="test-module-late",
            points_to_pass=50,
            course_instance=self.current_course_instance,
            opening_time=self.today,
            closing_time=self.tomorrow,
            late_submissions_allowed=True,
            late_submission_deadline=self.two_days_from_now,
            late_submission_penalty=0.2
        )

        self.learning_object_category = LearningObjectCategory.objects.create(
            name="test category",
            course_instance=self.current_course_instance,
            points_to_pass=5
        )

        #self.hidden_learning_object_category = LearningObjectCategory.objects.create(
        #    name="hidden category",
        #    course_instance=self.current_course_instance
        #)
        #self.hidden_learning_object_category.hidden_to.add(self.user.userprofile)

        self.learning_object = LearningObject.objects.create(
            name="test learning object",
            course_module=self.course_module,
            category=self.learning_object_category,
            url='l1',
        )

        self.broken_learning_object = LearningObject.objects.create(
            name="test learning object",
            course_module=self.course_module_with_late_submissions_allowed,
            category=self.learning_object_category,
            url='l2',
        )

        self.base_exercise = BaseExercise.objects.create(
            name="test exercise",
            course_module=self.course_module,
            category=self.learning_object_category,
            service_url="http://localhost/",
            url='b1',
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
        self.assertEqual("/Course-Url/T-00.1000_d1/", self.current_course_instance.get_absolute_url())
        self.assertEqual("/Course-Url/T-00.1000_hidden/", self.hidden_course_instance.get_absolute_url())

    def test_course_staff(self):
        self.assertFalse(self.course.is_teacher(self.user))
        self.assertFalse(self.current_course_instance.is_assistant(self.user))
        self.assertFalse(self.current_course_instance.is_teacher(self.user))
        self.assertFalse(self.current_course_instance.is_course_staff(self.user))
        self.assertEqual(0, len(self.current_course_instance.get_course_staff_profiles()))

        self.current_course_instance.assistants.add(self.user.userprofile)

        self.assertFalse(self.course.is_teacher(self.user))
        self.assertTrue(self.current_course_instance.is_assistant(self.user))
        self.assertFalse(self.current_course_instance.is_teacher(self.user))
        self.assertTrue(self.current_course_instance.is_course_staff(self.user))
        self.assertEqual(1, len(self.current_course_instance.get_course_staff_profiles()))

        self.course.teachers.add(self.user.userprofile)

        self.assertTrue(self.course.is_teacher(self.user))
        self.assertTrue(self.current_course_instance.is_assistant(self.user))
        self.assertTrue(self.current_course_instance.is_teacher(self.user))
        self.assertTrue(self.current_course_instance.is_course_staff(self.user))
        self.assertEqual(1, len(self.current_course_instance.get_course_staff_profiles()))
        self.assertEqual("testUser", self.current_course_instance.get_course_staff_profiles()[0].shortname)

        self.current_course_instance.assistants.clear()

        self.assertTrue(self.course.is_teacher(self.user))
        self.assertFalse(self.current_course_instance.is_assistant(self.user))
        self.assertTrue(self.current_course_instance.is_teacher(self.user))
        self.assertTrue(self.current_course_instance.is_course_staff(self.user))
        self.assertEqual(1, len(self.current_course_instance.get_course_staff_profiles()))

        self.course.teachers.clear()

        self.assertFalse(self.course.is_teacher(self.user))
        self.assertFalse(self.current_course_instance.is_assistant(self.user))
        self.assertFalse(self.current_course_instance.is_teacher(self.user))
        self.assertFalse(self.current_course_instance.is_course_staff(self.user))
        self.assertEqual(0, len(self.current_course_instance.get_course_staff_profiles()))

    def test_course_instance_submitters(self):
        students = self.current_course_instance.get_submitted_profiles()
        self.assertEqual(1, len(students))
        self.assertEqual("testUser", students[0].shortname)

        submission2 = Submission.objects.create(
            exercise=self.base_exercise,
            grader=self.grader.userprofile)
        submission2.submitters.add(self.user.userprofile)

        students = self.current_course_instance.get_submitted_profiles()
        self.assertEqual(1, len(students))
        self.assertEqual("testUser", students[0].shortname)

        submission3 = Submission.objects.create(
            exercise=self.base_exercise,
            grader=self.user.userprofile)
        submission3.submitters.add(self.grader.userprofile)

        students = self.current_course_instance.get_submitted_profiles()
        self.assertEqual(2, len(students))
        self.assertEqual("testUser", students[0].shortname)
        self.assertEqual("grader", students[1].shortname)

    def test_course_instance_visibility(self):
        self.assertTrue(self.current_course_instance.is_visible_to())
        self.assertFalse(self.hidden_course_instance.is_visible_to())
        self.assertTrue(self.current_course_instance.is_visible_to(self.user))
        self.assertFalse(self.hidden_course_instance.is_visible_to(self.user))
        self.assertTrue(self.current_course_instance.is_visible_to(self.superuser))
        self.assertTrue(self.hidden_course_instance.is_visible_to(self.superuser))

    def test_course_instance_get_visible(self):
        open_course_instances = CourseInstance.objects.get_visible()
        self.assertEqual(3, len(open_course_instances))
        self.assertTrue(self.current_course_instance in open_course_instances)
        self.assertTrue(self.future_course_instance in open_course_instances)

        open_course_instances = CourseInstance.objects.get_visible(self.user)
        self.assertEqual(3, len(open_course_instances))
        self.assertTrue(self.current_course_instance in open_course_instances)
        self.assertTrue(self.future_course_instance in open_course_instances)

        open_course_instances = CourseInstance.objects.get_visible(self.superuser)
        self.assertEqual(4, len(open_course_instances))
        self.assertTrue(self.current_course_instance in open_course_instances)
        self.assertTrue(self.future_course_instance in open_course_instances)
        self.assertTrue(self.hidden_course_instance in open_course_instances)

    def test_course_instance_unicode_string(self):
        self.assertEqual("123456 test course: Fall 2011 day 1", str(self.current_course_instance))
        self.assertEqual("123456 test course: Secret super course", str(self.hidden_course_instance))

    def test_course_hook_unicode_string(self):
        self.assertEqual("123456 test course: Fall 2011 day 1 -> test_hook_url", str(self.course_hook))

    def test_course_module_late_submission_point_worth(self):
        self.assertEqual(0, self.course_module.get_late_submission_point_worth())
        self.assertEqual(80, self.course_module_with_late_submissions_allowed.get_late_submission_point_worth())

    def test_course_module_open(self):
        self.assertFalse(self.course_module.is_open(self.yesterday))
        self.assertTrue(self.course_module.is_open(self.today))
        self.assertTrue(self.course_module.is_open())
        self.assertTrue(self.course_module.is_open(self.tomorrow))
        self.assertFalse(self.course_module.is_open(self.two_days_from_now))

    def test_course_module_after_open(self):
        self.assertFalse(self.course_module.is_after_open(self.yesterday))
        self.assertTrue(self.course_module.is_after_open(self.today))
        self.assertTrue(self.course_module.is_after_open())
        self.assertTrue(self.course_module.is_after_open(self.tomorrow))
        self.assertTrue(self.course_module.is_after_open(self.two_days_from_now))

    def test_course_views(self):
        response = self.client.get('/no_course/test', follow=True)
        self.assertEqual(response.status_code, 404)
        response = self.client.get(self.current_course_instance.get_absolute_url(), follow=True)
        self.assertTrue(response.redirect_chain)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'userprofile/login.html')

        self.client.login(username="testUser", password="testPassword")
        response = self.client.get('/no_course/test', follow=True)
        self.assertEqual(response.status_code, 404)
        response = self.client.get(self.current_course_instance.get_absolute_url(), follow=True)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.context["course"], self.course)
        self.assertEqual(response.context["instance"], self.current_course_instance)
        self.assertFalse(response.context["is_assistant"])
        self.assertFalse(response.context["is_teacher"])

        response = self.client.get(self.hidden_course_instance.get_absolute_url(), follow=True)
        self.assertEqual(response.status_code, 403)

    def test_course_teacher_views(self):
        url = self.current_course_instance.get_edit_url()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        self.client.login(username="testUser", password="testPassword")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        self.current_course_instance.assistants.add(self.grader.userprofile)
        self.client.login(username="grader", password="graderPassword")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        response = self.client.get(self.current_course_instance.get_absolute_url(), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_assistant"])
        self.assertFalse(response.context["is_teacher"])

        self.current_course_instance.assistants.clear()
        self.course.teachers.add(self.grader.userprofile)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = self.client.get(self.current_course_instance.get_absolute_url(), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["is_assistant"])
        self.assertTrue(response.context["is_teacher"])

        self.client.logout()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        self.client.login(username="staff", password="staffPassword")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["is_assistant"])
        self.assertTrue(response.context["is_teacher"])

    def test_groups(self):
        group = StudentGroup(course_instance=self.current_course_instance)
        group.save()
        group.members.add(self.user.userprofile,self.grader.userprofile)
        self.assertEqual(StudentGroup.get_exact(self.current_course_instance,
            [self.user.userprofile,self.grader.userprofile]), group)
        self.assertEqual(StudentGroup.get_exact(self.current_course_instance,
            [self.user.userprofile,self.superuser.userprofile]), None)
