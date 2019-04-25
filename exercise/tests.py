from datetime import datetime, timedelta
import json
import os.path
import urllib

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.test import TestCase
from django.test.client import RequestFactory
from django.utils import timezone
from django.utils.datastructures import MultiValueDict

from course.models import Course, CourseInstance, CourseHook, CourseModule, \
    LearningObjectCategory
from deviations.models import DeadlineRuleDeviation, \
    MaxSubmissionsRuleDeviation
from exercise.exercise_summary import UserExerciseSummary
from exercise.models import BaseExercise, StaticExercise, \
    ExerciseWithAttachment, Submission, SubmittedFile, LearningObject
from exercise.protocol.exercise_page import ExercisePage


class ExerciseTest(TestCase):
    def setUp(self):
        self.user = User(username="testUser", first_name="First", last_name="Last")
        self.user.set_password("testPassword")
        self.user.save()

        self.grader = User(username="grader")
        self.grader.set_password("graderPassword")
        self.grader.save()

        self.teacher = User(username="staff", is_staff=True)
        self.teacher.set_password("staffPassword")
        self.teacher.save()

        self.user2 = User(username="testUser2", first_name="Strange", last_name="Fellow")
        self.user2.set_password("testPassword2")
        self.user2.save()

        self.course = Course.objects.create(
            name="test course",
            code="123456",
            url="Course-Url"
        )
        self.course.teachers.add(self.teacher.userprofile)

        self.today = timezone.now()
        self.yesterday = self.today - timedelta(days=1)
        self.tomorrow = self.today + timedelta(days=1)
        self.two_days_from_now = self.tomorrow + timedelta(days=1)
        self.three_days_from_now = self.two_days_from_now + timedelta(days=1)

        self.course_instance = CourseInstance.objects.create(
            instance_name="Fall 2011 day 1",
            starting_time=self.today,
            ending_time=self.tomorrow,
            course=self.course,
            url="T-00.1000_d1",
            view_content_to=CourseInstance.VIEW_ACCESS.ENROLLMENT_AUDIENCE,
        )
        self.course_instance.assistants.add(self.grader.userprofile)

        self.course_module = CourseModule.objects.create(
            name="test module",
            url="test-module",
            points_to_pass=15,
            course_instance=self.course_instance,
            opening_time=self.today,
            closing_time=self.tomorrow
        )

        self.course_module_with_late_submissions_allowed = CourseModule.objects.create(
            name="test module",
            url="test-module-late",
            points_to_pass=50,
            course_instance=self.course_instance,
            opening_time=self.today,
            closing_time=self.tomorrow,
            late_submissions_allowed=True,
            late_submission_deadline=self.two_days_from_now,
            late_submission_penalty=0.2
        )

        self.old_course_module = CourseModule.objects.create(
            name="test module",
            url="test-module-old",
            points_to_pass=15,
            course_instance=self.course_instance,
            opening_time=self.yesterday,
            closing_time=self.today
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
        #self.hidden_learning_object_category.hidden_to.add(self.user.userprofile)

        self.learning_object = LearningObject.objects.create(
            name="test learning object",
            course_module=self.course_module,
            category=self.learning_object_category,
            url="l1",
        )

        # Learning object names are not unique, so this object really is not
        # broken despite the variable name.
        self.broken_learning_object = LearningObject.objects.create(
            name="test learning object",
            course_module=self.course_module_with_late_submissions_allowed,
            category=self.learning_object_category,
            url="l2",
        )

        self.base_exercise = BaseExercise.objects.create(
            order=1,
            name="test exercise",
            course_module=self.course_module,
            category=self.learning_object_category,
            url="b1",
            max_submissions=1,
        )

        self.static_exercise = StaticExercise.objects.create(
            order=2,
            name="test exercise 2",
            course_module=self.course_module,
            category=self.learning_object_category,
            url="s2",
            max_points=50,
            points_to_pass=50,
            service_url="/testServiceURL",
            exercise_page_content="test_page_content",
            submission_page_content="test_submission_content"
        )

        self.exercise_with_attachment = ExerciseWithAttachment.objects.create(
            order=3,
            name="test exercise 3",
            course_module=self.course_module,
            category=self.learning_object_category,
            url="a1",
            max_points=50,
            points_to_pass=50,
            max_submissions=0,
            files_to_submit="test1.txt|test2.txt|img.png",
            content="test_instructions"
        )

        self.old_base_exercise = BaseExercise.objects.create(
            name="test exercise",
            course_module=self.old_course_module,
            category=self.learning_object_category,
            url="b2",
            max_submissions=1
        )

        self.base_exercise_with_late_submission_allowed = BaseExercise.objects.create(
            name="test exercise with late submissions allowed",
            course_module=self.course_module_with_late_submissions_allowed,
            category=self.learning_object_category,
            url="b3",
        )

        self.submission = Submission.objects.create(
            exercise=self.base_exercise,
            grader=self.grader.userprofile
        )
        self.submission.submitters.add(self.user.userprofile)

        self.submission_with_two_submitters = Submission.objects.create(
            exercise=self.base_exercise,
            grader=self.grader.userprofile
        )
        self.submission_with_two_submitters.submitters.add(self.user.userprofile)
        self.submission_with_two_submitters.submitters.add(self.user2.userprofile)

        self.late_submission = Submission.objects.create(
            exercise=self.base_exercise,
            grader=self.grader.userprofile
        )
        self.late_submission.submission_time = self.two_days_from_now
        self.late_submission.submitters.add(self.user.userprofile)

        self.submission_when_late_allowed = Submission.objects.create(
            exercise=self.base_exercise_with_late_submission_allowed,
            grader=self.grader.userprofile
        )
        self.submission_when_late_allowed.submitters.add(self.user.userprofile)

        self.late_submission_when_late_allowed = Submission.objects.create(
            exercise=self.base_exercise_with_late_submission_allowed,
            grader=self.grader.userprofile
        )
        self.late_submission_when_late_allowed.submission_time = self.two_days_from_now
        self.late_submission_when_late_allowed.submitters.add(self.user.userprofile)

        self.late_late_submission_when_late_allowed = Submission.objects.create(
            exercise=self.base_exercise_with_late_submission_allowed,
            grader=self.grader.userprofile
        )
        self.late_late_submission_when_late_allowed.submission_time = self.three_days_from_now
        self.late_late_submission_when_late_allowed.submitters.add(self.user.userprofile)

        self.course_hook = CourseHook.objects.create(
            hook_url="http://localhost/test_hook_url",
            course_instance=self.course_instance
        )

        self.deadline_rule_deviation = DeadlineRuleDeviation.objects.create(
            exercise=self.exercise_with_attachment,
            submitter=self.user.userprofile,
            extra_minutes=1440  # One day
        )

    def test_learning_object_category_unicode_string(self):
        self.assertEqual("test category", str(self.learning_object_category))
        self.assertEqual("hidden category", str(self.hidden_learning_object_category))

    #def test_learning_object_category_hiding(self):
    #    self.assertFalse(self.learning_object_category.is_hidden_to(self.user.userprofile))
    #    self.assertFalse(self.learning_object_category.is_hidden_to(self.grader.userprofile))
    #    self.assertTrue(self.hidden_learning_object_category.is_hidden_to(self.user.userprofile))
    #    self.assertFalse(self.hidden_learning_object_category.is_hidden_to(self.grader.userprofile))

    #    self.hidden_learning_object_category.set_hidden_to(self.user.userprofile, False)
    #    self.hidden_learning_object_category.set_hidden_to(self.grader.userprofile)

    #    self.assertFalse(self.hidden_learning_object_category.is_hidden_to(self.user.userprofile))
    #    self.assertTrue(self.hidden_learning_object_category.is_hidden_to(self.grader.userprofile))

    #    self.hidden_learning_object_category.set_hidden_to(self.user.userprofile, True)
    #    self.hidden_learning_object_category.set_hidden_to(self.grader.userprofile, False)

    #    self.assertTrue(self.hidden_learning_object_category.is_hidden_to(self.user.userprofile))
    #    self.assertFalse(self.hidden_learning_object_category.is_hidden_to(self.grader.userprofile))

    def test_learning_object_clean(self):
        try:
            self.learning_object.clean()
            self.broken_learning_object.clean() # should validate since it really is not broken
        except ValidationError:
            self.fail()

    def test_learning_object_course_instance(self):
        self.assertEqual(self.course_instance, self.learning_object.course_instance)
        self.assertEqual(self.course_instance, self.broken_learning_object.course_instance)

    def test_base_exercise_one_has_submissions(self):
        self.assertFalse(self.base_exercise.one_has_submissions([self.user.userprofile])[0])
        self.assertTrue(self.static_exercise.one_has_submissions([self.user.userprofile])[0])
        self.assertTrue(self.exercise_with_attachment.one_has_submissions([self.user.userprofile])[0])
        self.submission.set_error()
        self.submission.save()
        self.submission_with_two_submitters.set_error()
        self.submission_with_two_submitters.save()
        self.late_submission.set_error()
        self.late_submission.save()
        self.assertTrue(self.base_exercise.one_has_submissions([self.user.userprofile])[0])

    def test_base_exercise_max_submissions(self):
        self.assertEqual(1, self.base_exercise.max_submissions_for_student(self.user.userprofile))
        self.assertEqual(10, self.static_exercise.max_submissions_for_student(self.user.userprofile))
        self.assertEqual(0, self.exercise_with_attachment.max_submissions_for_student(self.user.userprofile))

    def test_base_exercise_submissions_for_student(self):
        self.assertEqual(3, len(self.base_exercise.get_submissions_for_student(self.user.userprofile)))
        self.assertEqual(0, len(self.static_exercise.get_submissions_for_student(self.user.userprofile)))
        self.assertEqual(0, len(self.exercise_with_attachment.get_submissions_for_student(self.user.userprofile)))
        self.submission.set_error()
        self.submission.save()
        self.assertEqual(3, len(self.base_exercise.get_submissions_for_student(self.user.userprofile)))
        self.assertEqual(2, len(self.base_exercise.get_submissions_for_student(self.user.userprofile, True)))

    def test_base_exercise_is_open(self):
        self.assertTrue(self.base_exercise.is_open())
        self.assertTrue(self.static_exercise.is_open())
        self.assertTrue(self.exercise_with_attachment.is_open())
        self.assertFalse(self.old_base_exercise.is_open())
        self.assertFalse(self.base_exercise.is_open(self.yesterday))
        self.assertFalse(self.static_exercise.is_open(self.yesterday))
        self.assertFalse(self.exercise_with_attachment.is_open(self.yesterday))
        self.assertTrue(self.old_base_exercise.is_open(self.yesterday))
        self.assertTrue(self.base_exercise.is_open(self.tomorrow))
        self.assertTrue(self.static_exercise.is_open(self.tomorrow))
        self.assertTrue(self.exercise_with_attachment.is_open(self.tomorrow))
        self.assertFalse(self.old_base_exercise.is_open(self.tomorrow))

    def test_base_exercise_one_has_access(self):
        self.assertTrue(self.base_exercise.one_has_access([self.user.userprofile])[0])
        self.assertTrue(self.static_exercise.one_has_access([self.user.userprofile])[0])
        self.assertTrue(self.exercise_with_attachment.one_has_access([self.user.userprofile])[0])
        self.assertFalse(self.old_base_exercise.one_has_access([self.user.userprofile])[0])
        self.assertFalse(self.base_exercise.one_has_access([self.user.userprofile], self.yesterday)[0])
        self.assertFalse(self.static_exercise.one_has_access([self.user.userprofile], self.yesterday)[0])
        self.assertFalse(self.exercise_with_attachment.one_has_access([self.user.userprofile], self.yesterday)[0])
        self.assertTrue(self.old_base_exercise.one_has_access([self.user.userprofile], self.yesterday)[0])
        self.assertTrue(self.base_exercise.one_has_access([self.user.userprofile], self.tomorrow)[0])
        self.assertTrue(self.static_exercise.one_has_access([self.user.userprofile], self.tomorrow)[0])
        self.assertTrue(self.exercise_with_attachment.one_has_access([self.user.userprofile], self.tomorrow)[0])
        self.assertFalse(self.old_base_exercise.one_has_access([self.user.userprofile], self.tomorrow)[0])

    def test_base_exercise_submission_allowed(self):
        status, errors, students = (
            self.base_exercise.check_submission_allowed(self.user.userprofile))
        self.assertNotEqual(status, self.base_exercise.SUBMIT_STATUS.ALLOWED)
        self.assertEqual(len(errors), 1)
        json.dumps(errors)
        self.assertNotEqual(
            self.static_exercise.check_submission_allowed(self.user.userprofile)[0],
            self.static_exercise.SUBMIT_STATUS.ALLOWED)
        self.course_instance.enroll_student(self.user)
        self.assertEqual(
            self.static_exercise.check_submission_allowed(self.user.userprofile)[0],
            self.static_exercise.SUBMIT_STATUS.ALLOWED)
        self.assertEqual(
            self.exercise_with_attachment.check_submission_allowed(self.user.userprofile)[0],
            self.static_exercise.SUBMIT_STATUS.ALLOWED)
        self.assertNotEqual(
            self.old_base_exercise.check_submission_allowed(self.user.userprofile)[0],
            self.old_base_exercise.SUBMIT_STATUS.ALLOWED)

        self.assertEqual(
            self.base_exercise.check_submission_allowed(self.grader.userprofile)[0],
            self.base_exercise.SUBMIT_STATUS.ALLOWED)
        self.assertEqual(
            self.static_exercise.check_submission_allowed(self.grader.userprofile)[0],
            self.static_exercise.SUBMIT_STATUS.ALLOWED)
        self.assertEqual(
            self.exercise_with_attachment \
                .check_submission_allowed(self.grader.userprofile)[0],
            self.exercise_with_attachment.SUBMIT_STATUS.ALLOWED)
        self.assertEqual(
            self.old_base_exercise.check_submission_allowed(self.grader.userprofile)[0],
            self.old_base_exercise.SUBMIT_STATUS.ALLOWED)

    def test_base_exercise_submission_deviation(self):
        self.assertFalse(self.base_exercise.one_has_submissions([self.user.userprofile])[0])
        deviation = MaxSubmissionsRuleDeviation.objects.create(
            exercise=self.base_exercise,
            submitter=self.user.userprofile,
            extra_submissions=3
        )
        self.assertTrue(self.base_exercise.one_has_submissions([self.user.userprofile])[0])

    def test_base_exercise_deadline_deviation(self):
        self.assertFalse(self.old_base_exercise.one_has_access([self.user.userprofile])[0])
        deviation = DeadlineRuleDeviation.objects.create(
            exercise=self.old_base_exercise,
            submitter=self.user.userprofile,
            extra_minutes=10*24*60
        )
        self.assertTrue(self.old_base_exercise.one_has_access([self.user.userprofile])[0])

    def test_base_exercise_total_submission_count(self):
        self.assertEqual(self.base_exercise.get_total_submitter_count(), 2)
        self.assertEqual(self.static_exercise.get_total_submitter_count(), 0)
        self.assertEqual(self.exercise_with_attachment.get_total_submitter_count(), 0)

    def test_base_exercise_unicode_string(self):
        self.assertEqual("1.1 test exercise", str(self.base_exercise))
        self.assertEqual("1.2 test exercise 2", str(self.static_exercise))
        self.assertEqual("1.3 test exercise 3", str(self.exercise_with_attachment))

    def test_base_exercise_absolute_url(self):
        self.assertEqual("/Course-Url/T-00.1000_d1/test-module/b1/", self.base_exercise.get_absolute_url())
        self.assertEqual("/Course-Url/T-00.1000_d1/test-module/s2/", self.static_exercise.get_absolute_url())
        self.assertEqual("/Course-Url/T-00.1000_d1/test-module/a1/", self.exercise_with_attachment.get_absolute_url())

    def test_base_exercise_async_url(self):
        request = RequestFactory().request(SERVER_NAME='localhost', SERVER_PORT='8001')
        language = 'en'
        # the order of the parameters in the returned service url is non-deterministic, so we check the parameters separately
        split_base_exercise_service_url = self.base_exercise._build_service_url(language, request, [self.user.userprofile], 1, 'exercise', 'service').split("?")
        split_static_exercise_service_url = self.static_exercise._build_service_url(language, request, [self.user.userprofile], 1, 'exercise', 'service').split("?")
        self.assertEqual("", split_base_exercise_service_url[0])
        self.assertEqual("/testServiceURL", split_static_exercise_service_url[0])
        # a quick hack to check whether the parameters are URL encoded
        self.assertFalse("/" in split_base_exercise_service_url[1] or ":" in split_base_exercise_service_url[1])
        self.assertFalse("/" in split_static_exercise_service_url[1] or ":" in split_static_exercise_service_url[1])
        # create dictionaries from the parameters and check each value. Note: parse_qs changes encoding back to regular utf-8
        base_exercise_url_params = urllib.parse.parse_qs(split_base_exercise_service_url[1])
        static_exercise_url_params = urllib.parse.parse_qs(split_static_exercise_service_url[1])
        self.assertEqual(['100'], base_exercise_url_params['max_points'])
        self.assertEqual('http://localhost:8001/service', base_exercise_url_params['submission_url'][0][:40])
        self.assertEqual(['50'], static_exercise_url_params['max_points'])
        self.assertEqual(['http://localhost:8001/service'], static_exercise_url_params['submission_url'])

    def test_static_exercise_load(self):
        request = RequestFactory().request(SERVER_NAME='localhost', SERVER_PORT='8001')
        static_exercise_page = self.static_exercise.load(request, [self.user.userprofile])
        self.assertIsInstance(static_exercise_page, ExercisePage)
        self.assertEqual("test_page_content", static_exercise_page.content)

    def test_static_exercise_grade(self):
        request = RequestFactory().request(SERVER_NAME='localhost', SERVER_PORT='8001')
        sub = Submission.objects.create_from_post(self.static_exercise, [self.user.userprofile], request)
        static_exercise_page = self.static_exercise.grade(request, sub)
        self.assertIsInstance(static_exercise_page, ExercisePage)
        self.assertTrue(static_exercise_page.is_accepted)
        self.assertEqual("test_submission_content", static_exercise_page.content)

    def test_exercise_upload_dir(self):
        from exercise.exercise_models import build_upload_dir
        self.assertEqual("course_instance_1/exercise_attachment_5/test_file_name",
                         build_upload_dir(self.exercise_with_attachment, "test_file_name"))

    def test_exercise_with_attachment_files_to_submit(self):
        files = self.exercise_with_attachment.get_files_to_submit()
        self.assertEqual(3, len(files))
        self.assertEqual("test1.txt", files[0])
        self.assertEqual("test2.txt", files[1])
        self.assertEqual("img.png", files[2])

    def test_exercise_with_attachment_load(self):
        request = RequestFactory().request(SERVER_NAME='localhost', SERVER_PORT='8001')
        exercise_with_attachment_page = self.exercise_with_attachment.load(request, [self.user.userprofile])
        self.assertIsInstance(exercise_with_attachment_page, ExercisePage)
        c = exercise_with_attachment_page.content
        self.assertTrue('test_instructions' in c)
        self.assertTrue('test1.txt' in c and 'test2.txt' in c and "img.png" in c)

    def test_submission_files(self):
        self.assertEqual(0, len(self.submission.files.all()))
        self.submission.add_files(MultiValueDict({
            "key1": ["test_file1.txt", "test_file2.txt"],
            "key2": ["test_image.png", "test_audio.wav", "test_pdf.pdf"]
        }))
        self.assertEqual(5, len(self.submission.files.all()))

    def test_submission_points(self):
        try:
            self.submission.set_points(10, 5)
            self.fail("Should not be able to set points higher than max points!")
        except AssertionError:
            self.submission.set_points(5, 10)
            self.assertEqual(50, self.submission.grade)
            self.late_submission_when_late_allowed.set_points(10, 10)
            self.assertEqual(80, self.late_submission_when_late_allowed.grade)

    def test_submission_late_penalty_applied(self):
        self.submission.set_points(5, 10)
        self.late_submission.set_points(5, 10)
        self.submission_when_late_allowed.set_points(5, 10)
        self.late_submission_when_late_allowed.set_points(5, 10)
        self.late_late_submission_when_late_allowed.set_points(5, 10)
        self.assertFalse(self.submission.late_penalty_applied)
        self.assertTrue(self.late_submission.late_penalty_applied is not None)
        self.assertAlmostEqual(self.late_submission.late_penalty_applied, 0.0)
        self.assertEqual(self.late_submission.service_points, 5)
        self.assertEqual(self.late_submission.grade, 50)
        self.assertFalse(self.submission_when_late_allowed.late_penalty_applied)
        self.assertTrue(self.late_submission_when_late_allowed.late_penalty_applied)
        self.assertTrue(self.late_late_submission_when_late_allowed.late_penalty_applied)
        self.assertAlmostEqual(self.late_late_submission_when_late_allowed.late_penalty_applied, 0.2)
        self.assertEqual(self.late_late_submission_when_late_allowed.service_points, 5)
        self.assertEqual(self.late_late_submission_when_late_allowed.grade, 40)
        deviation = DeadlineRuleDeviation.objects.create(
            exercise=self.base_exercise_with_late_submission_allowed,
            submitter=self.user.userprofile,
            extra_minutes=10*24*60,
            without_late_penalty=True
        )
        self.late_late_submission_when_late_allowed.set_points(5, 10)
        self.assertFalse(self.late_late_submission_when_late_allowed.late_penalty_applied)
        deviation.without_late_penalty=False
        deviation.save()
        self.late_late_submission_when_late_allowed.set_points(5, 10)
        self.assertAlmostEqual(self.late_late_submission_when_late_allowed.late_penalty_applied, 0.2)

    def test_early_submission(self):
        self.course_module_with_late_submissions_allowed.opening_time = self.tomorrow
        submission = Submission.objects.create(
            exercise=self.base_exercise_with_late_submission_allowed,
            grader=self.grader.userprofile
        )
        submission.submitters.add(self.grader.userprofile)
        submission.set_points(10, 10)
        self.assertFalse(submission.late_penalty_applied)

    def test_unofficial_submission(self):
        self.course_module_with_late_submissions_allowed.late_submissions_allowed = False
        self.course_module_with_late_submissions_allowed.save()
        self.learning_object_category.accept_unofficial_submits = True
        self.learning_object_category.save()

        self.late_submission_when_late_allowed.set_points(10, 10)
        self.late_submission_when_late_allowed.set_ready()
        self.late_submission_when_late_allowed.save()
        self.assertEqual(self.late_submission_when_late_allowed.grade, 100)
        self.assertEqual(self.late_submission_when_late_allowed.status, Submission.STATUS.UNOFFICIAL)
        summary = UserExerciseSummary(self.base_exercise_with_late_submission_allowed, self.user)
        self.assertEqual(summary.get_submission_count(), 3)
        self.assertEqual(summary.get_points(), 0) # unofficial points are not shown here
        self.assertFalse(summary.is_graded())
        self.assertTrue(summary.is_unofficial())

        self.submission_when_late_allowed.set_points(5, 10)
        self.submission_when_late_allowed.set_ready()
        self.submission_when_late_allowed.save()
        self.assertEqual(self.submission_when_late_allowed.grade, 50)
        self.assertEqual(self.submission_when_late_allowed.status, Submission.STATUS.READY)
        summary = UserExerciseSummary(self.base_exercise_with_late_submission_allowed, self.user)
        self.assertEqual(summary.get_points(), 50)
        self.assertTrue(summary.is_graded())
        self.assertFalse(summary.is_unofficial())

        sub = Submission.objects.create(
            exercise=self.base_exercise_with_late_submission_allowed,
            grader=self.grader.userprofile
        )
        sub.submission_time = self.two_days_from_now + timedelta(days = 1)
        sub.save()
        sub.submitters.add(self.user.userprofile)
        sub.set_points(10, 10)
        sub.save()
        summary = UserExerciseSummary(self.base_exercise_with_late_submission_allowed, self.user)
        self.assertEqual(summary.get_points(), 50)
        self.assertTrue(summary.is_graded())
        self.assertFalse(summary.is_unofficial())

    def test_unofficial_max_submissions(self):
        self.learning_object_category.accept_unofficial_submits = True
        self.learning_object_category.save()
        res = self.base_exercise.one_has_submissions([self.user.userprofile])
        self.assertFalse(res[0] and len(res[1]) == 0)
        self.submission.set_points(1, 10)
        self.submission.set_ready()
        self.submission.save()
        self.assertEqual(self.submission.status, Submission.STATUS.UNOFFICIAL)

    def test_submission_unicode_string(self):
        self.assertEqual("1", str(self.submission))
        self.assertEqual("2", str(self.submission_with_two_submitters))
        self.assertEqual("3", str(self.late_submission))
        self.assertEqual("4", str(self.submission_when_late_allowed))
        self.assertEqual("5", str(self.late_submission_when_late_allowed))
        self.assertEqual("6", str(self.late_late_submission_when_late_allowed))

    def test_submission_status(self):
        self.assertEqual("initialized", self.submission.status)
        self.assertFalse(self.submission.is_graded)
        self.submission.set_error()
        self.assertEqual("error", self.submission.status)
        self.assertFalse(self.submission.is_graded)
        self.submission.set_waiting()
        self.assertEqual("waiting", self.submission.status)
        self.assertFalse(self.submission.is_graded)
        self.submission.set_error()
        self.assertEqual("error", self.submission.status)
        self.assertFalse(self.submission.is_graded)
        self.assertEqual(None, self.submission.grading_time)
        self.submission.set_ready()
        self.assertIsInstance(self.submission.grading_time, datetime)
        self.assertEqual("ready", self.submission.status)
        self.assertTrue(self.submission.is_graded)

    def test_submission_absolute_url(self):
        self.assertEqual("/Course-Url/T-00.1000_d1/test-module/b1/submissions/1/", self.submission.get_absolute_url())
        self.assertEqual("/Course-Url/T-00.1000_d1/test-module/b1/submissions/3/", self.late_submission.get_absolute_url())

    def test_submission_upload_dir(self):
        from exercise.submission_models import build_upload_dir
        submitted_file1 = SubmittedFile.objects.create(
            submission=self.submission,
            param_name="testParam"
        )

        submitted_file2 = SubmittedFile.objects.create(
            submission=self.submission_with_two_submitters,
            param_name="testParam2"
        )
        self.assertEqual("course_instance_1/submissions/exercise_3/users_1/submission_1/test_file_name", build_upload_dir(submitted_file1, "test_file_name"))
        self.assertEqual("course_instance_1/submissions/exercise_3/users_1-4/submission_2/test_file_name", build_upload_dir(submitted_file2, "test_file_name"))

    def test_exercise_views(self):
        upcoming_module = CourseModule.objects.create(
            name="upcoming module",
            url="upcoming-module",
            points_to_pass=15,
            course_instance=self.course_instance,
            opening_time=self.two_days_from_now,
            closing_time=self.three_days_from_now
        )
        upcoming_static_exercise = StaticExercise.objects.create(
            name="upcoming exercise",
            course_module=upcoming_module,
            category=self.learning_object_category,
            url="sssss",
            max_points=50,
            points_to_pass=50,
            service_url="/testServiceURL",
            exercise_page_content="test_page_content",
            submission_page_content="test_submission_content"
        )
        self.submission_with_two_submitters.submitters.remove(self.user.userprofile)
        response = self.client.get(self.static_exercise.get_absolute_url())
        self.assertEqual(response.status_code, 302)

        self.client.login(username="testUser", password="testPassword")
        response = self.client.get(self.static_exercise.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["exercise"], self.static_exercise)
        response = self.client.get(upcoming_static_exercise.get_absolute_url())
        self.assertEqual(response.status_code, 403)
        response = self.client.get(self.submission.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["submission"], self.submission)
        response = self.client.get(self.submission_with_two_submitters.get_absolute_url())
        self.assertEqual(response.status_code, 403)

        self.client.login(username="staff", password="staffPassword")
        response = self.client.get(upcoming_static_exercise.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        response = self.client.get(self.submission.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        response = self.client.get(self.submission_with_two_submitters.get_absolute_url())
        self.assertEqual(response.status_code, 200)

        self.client.login(username="grader", password="graderPassword")
        response = self.client.get(upcoming_static_exercise.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        response = self.client.get(self.submission.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        response = self.client.get(self.submission_with_two_submitters.get_absolute_url())
        self.assertEqual(response.status_code, 200)

    def test_exercise_staff_views(self):
        self.other_instance = CourseInstance.objects.create(
            instance_name="Another",
            starting_time=self.today,
            ending_time=self.tomorrow,
            course=self.course,
            url="another"
        )
        self.other_instance.assistants.add(self.grader.userprofile)
        list_submissions_url = self.base_exercise.get_submission_list_url()
        assess_submission_url = self.submission.get_url('submission-assess')
        response = self.client.get(list_submissions_url)
        self.assertEqual(response.status_code, 302)

        self.client.login(username="testUser", password="testPassword")
        response = self.client.get(list_submissions_url)
        self.assertEqual(response.status_code, 403)
        response = self.client.get(assess_submission_url)
        self.assertEqual(response.status_code, 403)

        self.client.login(username="staff", password="staffPassword")
        response = self.client.get(list_submissions_url)
        self.assertEqual(response.status_code, 200)
        response = self.client.get(assess_submission_url)
        self.assertEqual(response.status_code, 200)

        self.client.login(username="grader", password="graderPassword")
        response = self.client.get(list_submissions_url)
        self.assertEqual(response.status_code, 200)
        response = self.client.get(assess_submission_url)
        self.assertEqual(response.status_code, 403)

        self.base_exercise.allow_assistant_grading = True
        self.base_exercise.save()
        response = self.client.get(assess_submission_url)
        self.assertEqual(response.status_code, 200)

        self.course_instance.assistants.clear()
        response = self.client.get(list_submissions_url)
        self.assertEqual(response.status_code, 403)

    def test_uploading_and_viewing_file(self):
        exercise = BaseExercise.objects.create(
            order=4,
            name="test exercise 4",
            course_module=self.course_module,
            category=self.learning_object_category,
            url="bbb",
            max_points=50,
            points_to_pass=50,
            max_submissions=0,
            service_url="http://nowhere.asdasfasf/testServiceURL",
        )
        png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x05\x00\x00\x00\x05\x08\x02\x00\x00\x00\x02\r\xb1\xb2\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x15IDAT\x08\xd7c`\xc0\n\xfe\xff\xff\x8f\xce\xc1"\x84\x05\x00\x00\xde\x7f\x0b\xf5<|+\x98\x00\x00\x00\x00IEND\xaeB`\x82'
        file_a = os.path.join(settings.MEDIA_ROOT, "test.png")
        file_b = os.path.join(settings.MEDIA_ROOT, "test.py")
        with open(file_a, "wb") as f:
            f.write(png)
        with open(file_b, "wb") as f:
            f.write("Tekijät ja Hyyppö".encode("latin1"))

        self.course_instance.enroll_student(self.user)
        self.client.login(username="testUser", password="testPassword")

        with open(file_a, "rb") as fa:
            with open(file_b, "rb") as fb:
                response = self.client.post(exercise.get_absolute_url(), {
                    "key": "value",
                    "file1": fa,
                    "file2": fb,
                })
        self.assertEqual(response.status_code, 302)

        subs = self.user.userprofile.submissions.filter(exercise=exercise.id)
        self.assertEqual(subs.count(), 1)
        sub = subs.first()

        self.assertEqual(sub.submission_data[0], ["key", "value"])
        self.assertEqual(sub.files.count(), 2)
        files = sub.files.all().order_by("param_name")

        self.assertEqual(files[0].param_name, "file1")
        response = self.client.get(files[0].get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")

        self.assertEqual(files[1].param_name, "file2")
        response = self.client.get(files[1].get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], 'text/plain; charset="UTF-8"')

        response = self.client.get(files[1].get_absolute_url() + "?download=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/octet-stream")
        self.assertTrue(response["Content-Disposition"].startswith("attachment; filename="))

        exercise.delete()

    def test_can_show_model_solutions(self):
        course_module_with_late_submissions_open = CourseModule.objects.create(
            name="test module late open",
            url="test-module-late-open",
            points_to_pass=50,
            course_instance=self.course_instance,
            opening_time=self.yesterday - timedelta(days=1),
            closing_time=self.yesterday,
            late_submissions_allowed=True,
            late_submission_deadline=self.tomorrow,
            late_submission_penalty=0.4,
        )
        course_module_with_late_submissions_closed = CourseModule.objects.create(
            name="test module late closed",
            url="test-module-late-closed",
            points_to_pass=50,
            course_instance=self.course_instance,
            opening_time=self.yesterday - timedelta(days=1),
            closing_time=self.yesterday,
            late_submissions_allowed=True,
            late_submission_deadline=self.today - timedelta(hours=1),
            late_submission_penalty=0.4,
        )
        base_exercise_with_late_open = BaseExercise.objects.create(
            name="test exercise late open",
            course_module=course_module_with_late_submissions_open,
            category=self.learning_object_category,
            url="blateopen",
            max_submissions=5,
        )
        base_exercise_with_late_closed = BaseExercise.objects.create(
            name="test exercise late closed",
            course_module=course_module_with_late_submissions_closed,
            category=self.learning_object_category,
            url="blateclosed",
            max_submissions=5,
        )

        self.assertFalse(self.base_exercise.can_show_model_solutions) # module is open
        self.assertFalse(self.base_exercise.can_show_model_solutions_to_student(self.user))
        self.assertTrue(self.old_base_exercise.can_show_model_solutions) # module is closed
        self.assertTrue(self.old_base_exercise.can_show_model_solutions_to_student(self.user))
        self.assertFalse(self.base_exercise_with_late_submission_allowed.can_show_model_solutions) # module is open
        self.assertFalse(self.base_exercise_with_late_submission_allowed.can_show_model_solutions_to_student(self.user))
        self.assertFalse(base_exercise_with_late_open.can_show_model_solutions)
        self.assertFalse(base_exercise_with_late_open.can_show_model_solutions_to_student(self.user))
        self.assertTrue(base_exercise_with_late_closed.can_show_model_solutions)
        self.assertTrue(base_exercise_with_late_closed.can_show_model_solutions_to_student(self.user))

        # The user has submitted alone and has no deadline extension.
        self.assertEqual(self.old_base_exercise.get_submissions_for_student(self.user.userprofile).count(), 0)
        submission1 = Submission.objects.create(
            exercise=self.old_base_exercise,
        )
        submission1.submitters.add(self.user.userprofile)
        self.assertTrue(self.old_base_exercise.can_show_model_solutions) # module is closed
        self.assertTrue(self.old_base_exercise.can_show_model_solutions_to_student(self.user))
        # Add a deadline extension that is still active.
        deadline_rule_deviation_old_base_exercise = DeadlineRuleDeviation.objects.create(
            exercise=self.old_base_exercise,
            submitter=self.user.userprofile,
            extra_minutes=1440, # One day
        )
        self.assertTrue(self.old_base_exercise.can_show_model_solutions)
        self.assertFalse(self.old_base_exercise.can_show_model_solutions_to_student(self.user))
        # Change the deadline extension so that it is not active anymore.
        self.old_course_module.closing_time = self.today - timedelta(hours=2)
        self.old_course_module.save()
        deadline_rule_deviation_old_base_exercise.delete()
        deadline_rule_deviation_old_base_exercise = DeadlineRuleDeviation.objects.create(
            exercise=self.old_base_exercise,
            submitter=self.user.userprofile,
            extra_minutes=10,
        )
        self.assertTrue(self.old_base_exercise.can_show_model_solutions)
        self.assertTrue(self.old_base_exercise.can_show_model_solutions_to_student(self.user))

        # Group submission
        submission2 = Submission.objects.create(
            exercise=base_exercise_with_late_closed,
        )
        submission2.submitters.add(self.user.userprofile, self.user2.userprofile)
        self.assertTrue(base_exercise_with_late_closed.can_show_model_solutions)
        self.assertTrue(base_exercise_with_late_closed.can_show_model_solutions_to_student(self.user))
        self.assertTrue(base_exercise_with_late_closed.can_show_model_solutions_to_student(self.user2))
        # Add a deadline extension to one group member. It affects all group members.
        # Note: deadline deviations are relative to the module closing time, not the late submission deadline.
        deadline_rule_deviation_ex_late_closed = DeadlineRuleDeviation.objects.create(
            exercise=base_exercise_with_late_closed,
            submitter=self.user.userprofile,
            extra_minutes=60*24*2,
        )
        self.assertTrue(base_exercise_with_late_closed.can_show_model_solutions)
        self.assertFalse(base_exercise_with_late_closed.can_show_model_solutions_to_student(self.user))
        self.assertFalse(base_exercise_with_late_closed.can_show_model_solutions_to_student(self.user2))
        # Change the deadline extension so that it is not active anymore.
        deadline_rule_deviation_ex_late_closed.delete()
        deadline_rule_deviation_ex_late_closed = DeadlineRuleDeviation.objects.create(
            exercise=base_exercise_with_late_closed,
            submitter=self.user.userprofile,
            extra_minutes=10,
        )
        self.assertTrue(base_exercise_with_late_closed.can_show_model_solutions)
        self.assertTrue(base_exercise_with_late_closed.can_show_model_solutions_to_student(self.user))
        self.assertTrue(base_exercise_with_late_closed.can_show_model_solutions_to_student(self.user2))

