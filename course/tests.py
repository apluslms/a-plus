from datetime import timedelta

from django.contrib.auth.models import User
from django.conf import settings
from django.urls import reverse
from django.test import TestCase, override_settings
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

        self.superuser = User(username="staff", is_staff=True, is_superuser=True)
        self.superuser.set_password("staffPassword")
        self.superuser.save()

        self.user1 = User(username="testUser1")
        self.user1.set_password("testPassword")
        self.user1.save()
        self.user1.userprofile.student_id = '333333'
        self.user1.userprofile.organization = settings.LOCAL_ORGANIZATION
        self.user1.userprofile.save()

        self.user2 = User(username="testUser2")
        self.user2.set_password("testPassword")
        self.user2.save()
        self.user2.userprofile.student_id = '555555'
        self.user2.userprofile.organization = settings.LOCAL_ORGANIZATION
        self.user2.userprofile.save()

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
            url="T-00.1000_d0",
            sis_id=456
        )

        self.current_course_instance = CourseInstance.objects.create(
            instance_name="Fall 2011 day 1",
            starting_time=self.today,
            ending_time=self.tomorrow,
            course=self.course,
            url="T-00.1000_d1",
            sis_id=123
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

        self.course_module_with_reading_open = CourseModule.objects.create(
            name="test module",
            url="test-module-reading-open",
            points_to_pass=10,
            course_instance=self.current_course_instance,
            opening_time=self.today,
            closing_time=self.tomorrow,
            reading_opening_time=self.yesterday
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
        self.assertFalse(self.current_course_instance.is_assistant(self.user))
        self.assertFalse(self.current_course_instance.is_teacher(self.user))
        self.assertFalse(self.current_course_instance.is_course_staff(self.user))
        self.assertEqual(0, len(self.current_course_instance.get_course_staff_profiles()))

        self.current_course_instance.add_assistant(self.user.userprofile)

        self.assertTrue(self.current_course_instance.is_assistant(self.user))
        self.assertFalse(self.current_course_instance.is_teacher(self.user))
        self.assertTrue(self.current_course_instance.is_course_staff(self.user))
        self.assertEqual(1, len(self.current_course_instance.get_course_staff_profiles()))

        self.current_course_instance.add_teacher(self.user.userprofile)

        self.assertFalse(self.current_course_instance.is_assistant(self.user))
        self.assertTrue(self.current_course_instance.is_teacher(self.user))
        self.assertTrue(self.current_course_instance.is_course_staff(self.user))
        self.assertEqual(1, len(self.current_course_instance.get_course_staff_profiles()))
        self.assertEqual("testUser", self.current_course_instance.get_course_staff_profiles()[0].shortname)

        self.current_course_instance.clear_assistants()

        self.assertFalse(self.current_course_instance.is_assistant(self.user))
        self.assertTrue(self.current_course_instance.is_teacher(self.user))
        self.assertTrue(self.current_course_instance.is_course_staff(self.user))
        self.assertEqual(1, len(self.current_course_instance.get_course_staff_profiles()))

        self.current_course_instance.clear_teachers()

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

    def test_course_module_open_with_reading_opening_time(self):
        self.assertTrue(self.course_module_with_reading_open.is_open(self.yesterday))
        self.assertTrue(self.course_module_with_reading_open.is_open(self.today))
        self.assertTrue(self.course_module_with_reading_open.is_open())
        self.assertTrue(self.course_module_with_reading_open.is_open(self.tomorrow))
        self.assertFalse(self.course_module_with_reading_open.is_open(self.two_days_from_now))

    def test_course_module_exercises_open(self):
        self.assertFalse(self.course_module.have_exercises_been_opened(self.yesterday))
        self.assertTrue(self.course_module.have_exercises_been_opened(self.today))
        self.assertTrue(self.course_module.have_exercises_been_opened())
        self.assertTrue(self.course_module.have_exercises_been_opened(self.tomorrow))
        self.assertTrue(self.course_module.have_exercises_been_opened(self.two_days_from_now))
        self.assertTrue(self.course_module.reading_opening_time is None)

    def test_course_module_exercises_open_with_reading_opening_time(self):
        self.assertFalse(self.course_module_with_reading_open.have_exercises_been_opened(self.yesterday))
        self.assertTrue(self.course_module_with_reading_open.have_exercises_been_opened(self.today))
        self.assertTrue(self.course_module_with_reading_open.have_exercises_been_opened())
        self.assertTrue(self.course_module_with_reading_open.have_exercises_been_opened(self.tomorrow))
        self.assertTrue(self.course_module_with_reading_open.have_exercises_been_opened(self.two_days_from_now))
        self.assertTrue(
            self.course_module_with_reading_open.opening_time
            > self.course_module_with_reading_open.reading_opening_time
        )

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

        self.current_course_instance.add_assistant(self.grader.userprofile)
        self.client.login(username="grader", password="graderPassword")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        response = self.client.get(self.current_course_instance.get_absolute_url(), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_assistant"])
        self.assertFalse(response.context["is_teacher"])

        self.current_course_instance.clear_assistants()
        self.current_course_instance.add_teacher(self.grader.userprofile)
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

    def test_student_enroll(self):
        self.assertFalse(self.current_course_instance.is_student(self.user1))
        self.assertFalse(self.current_course_instance.is_student(self.user2))
        self.client.login(username="staff", password="staffPassword")
        response = self.client.post( # pylint: disable=unused-variable
            reverse("enroll-students", kwargs={
                'course_slug': self.course.url,
                'instance_slug': self.current_course_instance.url,
            }),
            {'user_profiles': [self.user1.id, self.user2.id]}
        )
        self.assertTrue(self.current_course_instance.is_student(self.user1))
        self.assertTrue(self.current_course_instance.is_student(self.user2))

    @override_settings(SIS_PLUGIN_MODULE = 'course.sis_test')
    @override_settings(SIS_PLUGIN_CLASS = 'SisTest')
    def test_student_enroll_from_sis(self):
        self.assertFalse(self.current_course_instance.is_student(self.user1))
        self.assertFalse(self.current_course_instance.is_student(self.user2))
        self.client.login(username="staff", password="staffPassword")
        response = self.client.post( # pylint: disable=unused-variable
            reverse("enroll-students", kwargs={
                'course_slug': self.course.url,
                'instance_slug': self.current_course_instance.url,
            }),
            {'user_profiles': [ ], 'sis': '123'}
        )
        self.assertTrue(self.current_course_instance.is_student(self.user1))
        self.assertTrue(self.current_course_instance.is_student(self.user2))

        # Sisu import should not remove manually enrolled students
        self.past_course_instance.enroll_student(self.user1)
        self.assertTrue(self.past_course_instance.is_student(self.user1))
        response = self.client.post( # pylint: disable=unused-variable
            reverse("enroll-students", kwargs={
                'course_slug': self.course.url,
                'instance_slug': self.past_course_instance.url,
            }),
            {'user_profiles': [ ], 'sis': '456'}
        )
        self.assertTrue(self.past_course_instance.is_student(self.user1))

        # Test unenroll
        self.past_course_instance.enroll_student(self.user1, from_sis=True)
        self.past_course_instance.enroll_student(self.user2, from_sis=True)
        self.assertTrue(self.past_course_instance.is_student(self.user1))
        self.assertTrue(self.past_course_instance.is_student(self.user2))
        response = self.client.post( # pylint: disable=unused-variable
            reverse("enroll-students", kwargs={
                'course_slug': self.course.url,
                'instance_slug': self.past_course_instance.url,
            }),
            {'user_profiles': [ ], 'sis': '456'}
        )
        self.assertFalse(self.past_course_instance.is_student(self.user1))
        self.assertFalse(self.past_course_instance.is_student(self.user2))

    def test_last_instance_view_hidden_module(self):
        course = Course.objects.create(
            name="Last instance view course",
            code="111111",
            url="last_instance_view",
        )

        older_instance = CourseInstance.objects.create(
            instance_name="older instance",
            starting_time=self.today,
            ending_time=self.tomorrow,
            course=course,
            url="expected",
        )
        # Add a ready module to the older course instance.
        older_module = CourseModule.objects.create( # pylint: disable=unused-variable
            name="older module",
            url="older-module",
            points_to_pass=10,
            course_instance=older_instance,
            opening_time=self.today,
            closing_time=self.tomorrow,
            status=CourseModule.STATUS.READY,
        )

        newer_instance = CourseInstance.objects.create(
            instance_name="newer instance",
            starting_time=self.yesterday,
            ending_time=self.tomorrow,
            course=course,
            url="invalid",
        )
        # Add a hidden module to the newer course instance.
        newer_module = CourseModule.objects.create( # pylint: disable=unused-variable
            name="newer module",
            url="newer-module",
            points_to_pass=10,
            course_instance=newer_instance,
            opening_time=self.yesterday,
            closing_time=self.tomorrow,
            status=CourseModule.STATUS.HIDDEN,
        )


        response = self.client.get('/last_instance_view/', follow=True)
        self.assertEqual(response.status_code, 200)

        # The redirect should point to the older instance with a visible module.
        self.assertEqual(response.context['next'] , '/last_instance_view/expected/')

    def test_last_instance_view_not_yet_open_module(self):
        self.current_course_instance.enroll_student(self.user1)
        self.client.login(username='testUser1', password='testPassword')
        response = self.client.get('/Course-Url/', follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(response.redirect_chain[0][0], '/Course-Url/T-00.1000_d1/')

    def test_last_instance_view_open_modules(self):
        course = Course.objects.create(
            name="Last instance view course",
            code="CS-111111",
            url="cs-111111",
        )

        # Two years ago.
        instance1 = CourseInstance.objects.create(
            instance_name="Instance 1",
            starting_time=self.today - timedelta(weeks=105),
            ending_time=self.today - timedelta(weeks=91),
            course=course,
            url="instance1",
        )
        module1 = CourseModule.objects.create( # pylint: disable=unused-variable
            name="Module 1",
            url="module1",
            points_to_pass=10,
            course_instance=instance1,
            opening_time=self.today - timedelta(weeks=104),
            closing_time=self.today - timedelta(weeks=102),
            status=CourseModule.STATUS.READY,
        )

        # One year ago.
        instance2 = CourseInstance.objects.create(
            instance_name="Instance 2",
            starting_time=self.today - timedelta(weeks=53),
            ending_time=self.today - timedelta(weeks=39),
            course=course,
            url="instance2",
        )
        module2 = CourseModule.objects.create( # pylint: disable=unused-variable
            name="Module 2",
            url="module2",
            points_to_pass=10,
            course_instance=instance2,
            opening_time=self.today - timedelta(weeks=52),
            closing_time=self.today - timedelta(weeks=50),
            status=CourseModule.STATUS.READY,
        )

        # This course instance has just recently started.
        instance3 = CourseInstance.objects.create(
            instance_name="Instance 3",
            starting_time=self.today - timedelta(weeks=1),
            ending_time=self.today + timedelta(weeks=14),
            course=course,
            url="instance3",
        )
        module3 = CourseModule.objects.create( # pylint: disable=unused-variable
            name="Module 3",
            url="module3",
            points_to_pass=10,
            course_instance=instance3,
            opening_time=self.today - timedelta(days=6),
            closing_time=self.today + timedelta(weeks=1),
            status=CourseModule.STATUS.READY,
        )

        instance1.enroll_student(self.user1)
        instance2.enroll_student(self.user1)
        instance3.enroll_student(self.user1)
        self.client.login(username='testUser1', password='testPassword')
        response = self.client.get('/cs-111111/', follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(response.redirect_chain[0][0], '/cs-111111/instance3/')

    def test_last_instance_view_almost_concurrent_instances(self):
        course = Course.objects.create(
            name="Last instance view course",
            code="CS-111111",
            url="cs-111111",
        )

        # One year ago.
        instance1 = CourseInstance.objects.create(
            instance_name="Instance 1",
            starting_time=self.today - timedelta(weeks=54),
            ending_time=self.today - timedelta(weeks=47),
            course=course,
            url="instance1",
        )
        module1 = CourseModule.objects.create( # pylint: disable=unused-variable
            name="Module 1",
            url="module1",
            points_to_pass=10,
            course_instance=instance1,
            opening_time=self.today - timedelta(weeks=54),
            closing_time=self.today - timedelta(weeks=51),
            status=CourseModule.STATUS.READY,
        )

        # Two course instances this year.
        instance2 = CourseInstance.objects.create(
            instance_name="Instance 2",
            starting_time=self.today - timedelta(weeks=3),
            ending_time=self.today + timedelta(weeks=4),
            course=course,
            url="instance2",
        )
        module2 = CourseModule.objects.create( # pylint: disable=unused-variable
            name="Module 2",
            url="module2",
            points_to_pass=10,
            course_instance=instance2,
            opening_time=self.today - timedelta(weeks=2),
            closing_time=self.today - timedelta(days=1),
            status=CourseModule.STATUS.READY,
        )
        module2b = CourseModule.objects.create( # pylint: disable=unused-variable
            name="Module 2b",
            url="module2b",
            points_to_pass=20,
            course_instance=instance2,
            opening_time=self.today + timedelta(days=1),
            closing_time=self.today + timedelta(weeks=1),
            status=CourseModule.STATUS.READY,
        )

        instance3 = CourseInstance.objects.create(
            instance_name="Instance 3",
            starting_time=self.today - timedelta(weeks=10),
            ending_time=self.today,
            course=course,
            url="instance3",
        )
        module3 = CourseModule.objects.create( # pylint: disable=unused-variable
            name="Module 3",
            url="module3",
            points_to_pass=10,
            course_instance=instance3,
            opening_time=self.today - timedelta(weeks=10),
            closing_time=self.today - timedelta(weeks=1),
            status=CourseModule.STATUS.READY,
        )

        instance1.enroll_student(self.user1)
        instance2.enroll_student(self.user1)
        instance3.enroll_student(self.user1)
        self.client.login(username='testUser1', password='testPassword')
        response = self.client.get('/cs-111111/', follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(response.redirect_chain[0][0], '/cs-111111/instance2/')

    def test_last_instance_view_only_future_instances(self):
        course = Course.objects.create(
            name="Last instance view course",
            code="CS-111111",
            url="cs-111111",
        )

        # Starting in a month.
        instance1 = CourseInstance.objects.create(
            instance_name="Instance 1",
            starting_time=self.today + timedelta(weeks=4),
            ending_time=self.today + timedelta(weeks=19),
            course=course,
            url="instance1",
        )
        module1 = CourseModule.objects.create( # pylint: disable=unused-variable
            name="Module 1",
            url="module1",
            points_to_pass=10,
            course_instance=instance1,
            opening_time=self.today + timedelta(weeks=4),
            closing_time=self.today + timedelta(weeks=18),
            status=CourseModule.STATUS.READY,
        )

        # Starts in a year.
        instance2 = CourseInstance.objects.create(
            instance_name="Instance 2",
            starting_time=self.today + timedelta(weeks=53),
            ending_time=self.today + timedelta(weeks=60),
            course=course,
            url="instance2",
        )
        module2 = CourseModule.objects.create( # pylint: disable=unused-variable
            name="Module 2",
            url="module2",
            points_to_pass=10,
            course_instance=instance2,
            opening_time=self.today + timedelta(weeks=53),
            closing_time=self.today + timedelta(weeks=56),
            status=CourseModule.STATUS.UNLISTED,
        )
        module2b = CourseModule.objects.create( # pylint: disable=unused-variable
            name="Module 2b",
            url="module2b",
            points_to_pass=20,
            course_instance=instance2,
            opening_time=self.today + timedelta(weeks=56),
            closing_time=self.today + timedelta(weeks=59),
            status=CourseModule.STATUS.HIDDEN,
        )

        # Starts after instance2.
        instance3 = CourseInstance.objects.create(
            instance_name="Instance 3",
            starting_time=self.today + timedelta(weeks=61),
            ending_time=self.today + timedelta(weeks=70),
            course=course,
            url="instance3",
        )
        module3 = CourseModule.objects.create( # pylint: disable=unused-variable
            name="Module 3",
            url="module3",
            points_to_pass=10,
            course_instance=instance3,
            opening_time=self.today + timedelta(weeks=61),
            closing_time=self.today + timedelta(weeks=70),
            status=CourseModule.STATUS.HIDDEN,
        )

        instance1.enroll_student(self.user1)
        instance2.enroll_student(self.user1)
        instance3.enroll_student(self.user1)
        self.client.login(username='testUser1', password='testPassword')
        response = self.client.get('/cs-111111/', follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.redirect_chain), 1)
        # This is not ideal, but this is how it currently works.
        # All instances start in the future, thus the latest instance is
        # the one that has the very latest starting time even though
        # there are earlier course instances that would start sooner.
        # It could make sense if the redirect targeted the next course instance
        # that is about to start soon.
        self.assertEqual(response.redirect_chain[0][0], '/cs-111111/instance3/')

        # Make the future course instances hidden from students except
        # the one that starts soon.
        instance2.visible_to_students = False
        instance2.save()
        instance3.visible_to_students = False
        instance3.save()

        response = self.client.get('/cs-111111/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(response.redirect_chain[0][0], '/cs-111111/instance1/')

    def test_last_instance_view_after_instance_ending(self):
        course = Course.objects.create(
            name="Last instance view course",
            code="CS-111111",
            url="cs-111111",
        )

        # One year ago.
        instance1 = CourseInstance.objects.create(
            instance_name="Instance 1",
            starting_time=self.today - timedelta(weeks=52),
            ending_time=self.today - timedelta(weeks=40),
            course=course,
            url="instance1",
        )
        module1 = CourseModule.objects.create( # pylint: disable=unused-variable
            name="Module 1",
            url="module1",
            points_to_pass=10,
            course_instance=instance1,
            opening_time=self.today - timedelta(weeks=51),
            closing_time=self.today - timedelta(weeks=41),
            status=CourseModule.STATUS.READY,
        )

        # Ended recently.
        instance2 = CourseInstance.objects.create(
            instance_name="Instance 2",
            starting_time=self.today - timedelta(weeks=15),
            ending_time=self.today - timedelta(weeks=1),
            course=course,
            url="instance2",
        )
        module2 = CourseModule.objects.create( # pylint: disable=unused-variable
            name="Module 2",
            url="module2",
            points_to_pass=10,
            course_instance=instance2,
            opening_time=self.today - timedelta(weeks=15),
            closing_time=self.today - timedelta(weeks=12),
            status=CourseModule.STATUS.READY,
        )
        module2b = CourseModule.objects.create( # pylint: disable=unused-variable
            name="Module 2b",
            url="module2b",
            points_to_pass=20,
            course_instance=instance2,
            opening_time=self.today - timedelta(weeks=12),
            closing_time=self.today - timedelta(weeks=1),
            status=CourseModule.STATUS.UNLISTED,
        )

        # Starts in 6 months.
        instance3 = CourseInstance.objects.create(
            instance_name="Instance 3",
            starting_time=self.today + timedelta(weeks=25),
            ending_time=self.today + timedelta(weeks=40),
            course=course,
            url="instance3",
        )
        module3 = CourseModule.objects.create( # pylint: disable=unused-variable
            name="Module 3",
            url="module3",
            points_to_pass=10,
            course_instance=instance3,
            opening_time=self.today + timedelta(weeks=25),
            closing_time=self.today + timedelta(weeks=30),
            status=CourseModule.STATUS.READY,
        )

        instance1.enroll_student(self.user1)
        instance2.enroll_student(self.user1)
        self.client.login(username='testUser1', password='testPassword')
        response = self.client.get('/cs-111111/', follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(response.redirect_chain[0][0], '/cs-111111/instance2/')

        # Hide instance2 from students.
        instance2.visible_to_students = False
        instance2.save()

        response = self.client.get('/cs-111111/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(response.redirect_chain[0][0], '/cs-111111/instance1/')

    def test_last_instance_view_all_instances_hidden(self):
        course = Course.objects.create(
            name="Last instance view course",
            code="CS-111111",
            url="cs-111111",
        )

        # One year ago.
        instance1 = CourseInstance.objects.create(
            visible_to_students=False,
            instance_name="Instance 1",
            starting_time=self.today - timedelta(weeks=52),
            ending_time=self.today - timedelta(weeks=40),
            course=course,
            url="instance1",
        )
        module1 = CourseModule.objects.create( # pylint: disable=unused-variable
            name="Module 1",
            url="module1",
            points_to_pass=10,
            course_instance=instance1,
            opening_time=self.today - timedelta(weeks=51),
            closing_time=self.today - timedelta(weeks=41),
            status=CourseModule.STATUS.READY,
        )

        # Ended recently.
        instance2 = CourseInstance.objects.create(
            visible_to_students=False,
            instance_name="Instance 2",
            starting_time=self.today - timedelta(weeks=15),
            ending_time=self.today - timedelta(weeks=1),
            course=course,
            url="instance2",
        )
        module2 = CourseModule.objects.create( # pylint: disable=unused-variable
            name="Module 2",
            url="module2",
            points_to_pass=10,
            course_instance=instance2,
            opening_time=self.today - timedelta(weeks=15),
            closing_time=self.today - timedelta(weeks=12),
            status=CourseModule.STATUS.READY,
        )
        module2b = CourseModule.objects.create( # pylint: disable=unused-variable
            name="Module 2b",
            url="module2b",
            points_to_pass=20,
            course_instance=instance2,
            opening_time=self.today - timedelta(weeks=12),
            closing_time=self.today - timedelta(weeks=1),
            status=CourseModule.STATUS.READY,
        )

        # Starts in 6 months.
        instance3 = CourseInstance.objects.create(
            visible_to_students=False,
            instance_name="Instance 3",
            starting_time=self.today + timedelta(weeks=25),
            ending_time=self.today + timedelta(weeks=40),
            course=course,
            url="instance3",
        )
        module3 = CourseModule.objects.create( # pylint: disable=unused-variable
            name="Module 3",
            url="module3",
            points_to_pass=10,
            course_instance=instance3,
            opening_time=self.today + timedelta(weeks=25),
            closing_time=self.today + timedelta(weeks=30),
            status=CourseModule.STATUS.READY,
        )

        instance1.enroll_student(self.user1)
        instance2.enroll_student(self.user1)
        self.client.login(username='testUser1', password='testPassword')
        response = self.client.get('/cs-111111/', follow=True)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(len(response.redirect_chain), 0)

        # Show all course instances from students.
        instance1.visible_to_students = True
        instance1.save()
        instance2.visible_to_students = True
        instance2.save()
        instance3.visible_to_students = True
        instance3.save()

        response = self.client.get('/cs-111111/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(response.redirect_chain[0][0], '/cs-111111/instance2/')

        instance1.visible_to_students = False
        instance1.save()
        instance2.visible_to_students = False
        instance2.save()
        instance3.visible_to_students = False
        instance3.save()

        # Log in as a teacher.
        self.client.logout()
        instance1.add_teacher(self.user.userprofile)
        instance2.add_teacher(self.user.userprofile)
        instance3.add_teacher(self.user.userprofile)
        self.client.login(username='testUser', password='testPassword')

        response = self.client.get('/cs-111111/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(response.redirect_chain[0][0], '/cs-111111/instance3/')

        instance1.visible_to_students = True
        instance1.save()
        instance2.visible_to_students = True
        instance2.save()
        instance3.visible_to_students = True
        instance3.save()

        response = self.client.get('/cs-111111/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(response.redirect_chain[0][0], '/cs-111111/instance2/')

    def test_last_instance_view_no_instances(self):
        course = Course.objects.create(
            name="Last instance view course",
            code="CS-111111",
            url="cs-111111",
        )

        response = self.client.get('/cs-111111/', follow=True)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(len(response.redirect_chain), 0)

        self.client.login(username='testUser1', password='testPassword')
        response = self.client.get('/cs-111111/', follow=True)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(len(response.redirect_chain), 0)

        instance1 = CourseInstance.objects.create(
            visible_to_students=False,
            instance_name="Instance 1",
            starting_time=self.today - timedelta(weeks=15),
            ending_time=self.today + timedelta(weeks=1),
            course=course,
            url="instance1",
        )

        response = self.client.get('/cs-111111/', follow=True)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(len(response.redirect_chain), 0)

        # Show the course instance to students and the user should be redirected there.
        instance1.visible_to_students = True
        instance1.save()
        instance1.enroll_student(self.user1)

        response = self.client.get('/cs-111111/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(response.redirect_chain[0][0], '/cs-111111/instance1/')

    def test_last_instance_view_new_instance_has_closed_module(self):
        course = Course.objects.create(
            name="Last instance view course",
            code="CS-111111",
            url="cs-111111",
        )

        # One year ago.
        instance1 = CourseInstance.objects.create(
            instance_name="Instance 1",
            starting_time=self.today - timedelta(weeks=52),
            ending_time=self.today - timedelta(weeks=40),
            course=course,
            url="instance1",
        )
        module1 = CourseModule.objects.create( # pylint: disable=unused-variable
            name="Module 1",
            url="module1",
            points_to_pass=10,
            course_instance=instance1,
            opening_time=self.today - timedelta(weeks=51),
            closing_time=self.today - timedelta(weeks=41),
            status=CourseModule.STATUS.READY,
        )

        # Course instance has opened, but the modules have not yet opened.
        instance2 = CourseInstance.objects.create(
            instance_name="Instance 2",
            starting_time=self.today - timedelta(days=3),
            ending_time=self.today + timedelta(weeks=7),
            course=course,
            url="instance2",
        )
        module2 = CourseModule.objects.create(
            name="Module 2",
            url="module2",
            points_to_pass=10,
            course_instance=instance2,
            opening_time=self.today + timedelta(days=2),
            closing_time=self.today + timedelta(weeks=3),
            status=CourseModule.STATUS.READY,
        )
        module2b = CourseModule.objects.create( # pylint: disable=unused-variable
            name="Module 2b",
            url="module2b",
            points_to_pass=20,
            course_instance=instance2,
            opening_time=self.today + timedelta(weeks=2),
            closing_time=self.today + timedelta(weeks=6),
            status=CourseModule.STATUS.READY,
        )

        # Starts in 6 months.
        instance3 = CourseInstance.objects.create(
            instance_name="Instance 3",
            starting_time=self.today + timedelta(weeks=25),
            ending_time=self.today + timedelta(weeks=40),
            course=course,
            url="instance3",
        )
        module3 = CourseModule.objects.create( # pylint: disable=unused-variable
            name="Module 3",
            url="module3",
            points_to_pass=10,
            course_instance=instance3,
            opening_time=self.today + timedelta(weeks=25),
            closing_time=self.today + timedelta(weeks=30),
            status=CourseModule.STATUS.READY,
        )

        instance1.enroll_student(self.user1)
        instance2.enroll_student(self.user1)
        self.client.login(username='testUser1', password='testPassword')
        response = self.client.get('/cs-111111/', follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(response.redirect_chain[0][0], '/cs-111111/instance1/')

        # Move the module opening time in instance2 so that it has already opened.
        module2.opening_time = self.today - timedelta(days=1)
        module2.save()

        response = self.client.get('/cs-111111/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(response.redirect_chain[0][0], '/cs-111111/instance2/')
