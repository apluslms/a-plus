import json
import urllib
from datetime import datetime, timedelta
from io import BytesIO, StringIO

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test.client import RequestFactory
from django.utils import timezone
from django.utils.datastructures import MultiValueDict

from course.models import Course, CourseInstance, CourseHook, CourseModule, \
    LearningObjectCategory
from deviations.models import DeadlineRuleDeviation, \
    MaxSubmissionsRuleDeviation
from exercise.cache.points import ExercisePoints
from exercise.exercise_models import build_upload_dir
from exercise.models import BaseExercise, StaticExercise, \
    ExerciseWithAttachment, Submission, SubmittedFile, LearningObject, \
    RevealRule, CourseChapter
from exercise.protocol.exercise_page import ExercisePage
from exercise.reveal_states import ExerciseRevealState, ModuleRevealState
from exercise.submission_models import build_upload_dir as build_upload_dir_for_submission_model
from lib.helpers import build_aplus_url

class ExerciseTestBase(TestCase):
    @classmethod
    def setUpTestData(cls): # pylint: disable=too-many-statements
        cls.user = User(username="testUser", first_name="First", last_name="Last")
        cls.user.set_password("testPassword")
        cls.user.save()
        cls.user.userprofile.student_id = '123456'
        cls.user.userprofile.organization = settings.LOCAL_ORGANIZATION
        cls.user.userprofile.save()

        cls.grader = User(username="grader")
        cls.grader.set_password("graderPassword")
        cls.grader.save()

        cls.teacher = User(username="staff", is_staff=True)
        cls.teacher.set_password("staffPassword")
        cls.teacher.save()

        cls.user2 = User(username="testUser2", first_name="Strange", last_name="Fellow")
        cls.user2.set_password("testPassword2")
        cls.user2.save()
        cls.user2.userprofile.student_id = '654321'
        cls.user2.userprofile.organization = settings.LOCAL_ORGANIZATION
        cls.user2.userprofile.save()

        cls.course = Course.objects.create(
            name="test course",
            code="123456",
            url="Course-Url"
        )

        cls.today = timezone.now()
        cls.yesterday = cls.today - timedelta(days=1)
        cls.tomorrow = cls.today + timedelta(days=1)
        cls.two_days_from_now = cls.tomorrow + timedelta(days=1)
        cls.three_days_from_now = cls.two_days_from_now + timedelta(days=1)

        cls.course_instance = CourseInstance.objects.create(
            instance_name="Fall 2011 day 1",
            enrollment_starting_time=cls.yesterday,
            starting_time=cls.today,
            ending_time=cls.tomorrow,
            course=cls.course,
            url="T-00.1000_d1",
            view_content_to=CourseInstance.VIEW_ACCESS.ENROLLMENT_AUDIENCE,
        )
        cls.course_instance.add_teacher(cls.teacher.userprofile)
        cls.course_instance.add_assistant(cls.grader.userprofile)

        cls.course_module = CourseModule.objects.create(
            name="test module",
            url="test-module",
            points_to_pass=15,
            course_instance=cls.course_instance,
            opening_time=cls.today,
            closing_time=cls.tomorrow
        )

        cls.course_module_with_late_submissions_allowed = CourseModule.objects.create(
            name="test module",
            url="test-module-late",
            points_to_pass=50,
            course_instance=cls.course_instance,
            opening_time=cls.today,
            closing_time=cls.tomorrow,
            late_submissions_allowed=True,
            late_submission_deadline=cls.two_days_from_now,
            late_submission_penalty=0.2
        )

        cls.old_course_module = CourseModule.objects.create(
            name="test module",
            url="test-module-old",
            points_to_pass=15,
            course_instance=cls.course_instance,
            opening_time=cls.yesterday,
            closing_time=cls.today
        )

        cls.reading_open_course_module = CourseModule.objects.create(
            name="test module",
            url="test-module-reading-open",
            points_to_pass=15,
            course_instance=cls.course_instance,
            reading_opening_time=cls.yesterday,
            opening_time=cls.tomorrow,
            closing_time=cls.two_days_from_now
        )

        cls.learning_object_category = LearningObjectCategory.objects.create(
            name="test category",
            course_instance=cls.course_instance,
            points_to_pass=5
        )

        cls.hidden_learning_object_category = LearningObjectCategory.objects.create(
            name="hidden category",
            course_instance=cls.course_instance
        )
        #cls.hidden_learning_object_category.hidden_to.add(cls.user.userprofile)

        cls.learning_object = LearningObject.objects.create(
            name="test learning object",
            course_module=cls.course_module,
            category=cls.learning_object_category,
            url="l1",
        )

        # Learning object names are not unique, so this object really is not
        # broken despite the variable name.
        cls.broken_learning_object = LearningObject.objects.create(
            name="test learning object",
            course_module=cls.course_module_with_late_submissions_allowed,
            category=cls.learning_object_category,
            url="l2",
        )

        cls.base_exercise = BaseExercise.objects.create(
            order=1,
            name="test exercise",
            course_module=cls.course_module,
            category=cls.learning_object_category,
            url="b1",
            max_submissions=1,
        )

        cls.static_exercise = StaticExercise.objects.create(
            order=2,
            name="test exercise 2",
            course_module=cls.course_module,
            category=cls.learning_object_category,
            url="s2",
            max_points=50,
            points_to_pass=50,
            service_url="/testServiceURL",
            exercise_page_content="test_page_content",
            submission_page_content="test_submission_content"
        )

        cls.exercise_with_attachment = ExerciseWithAttachment.objects.create(
            order=3,
            name="test exercise 3",
            course_module=cls.course_module,
            category=cls.learning_object_category,
            url="a1",
            max_points=50,
            points_to_pass=50,
            max_submissions=0,
            files_to_submit="test1.txt|test2.txt|img.png",
            content="test_instructions"
        )

        cls.old_base_exercise = BaseExercise.objects.create(
            name="test exercise",
            course_module=cls.old_course_module,
            category=cls.learning_object_category,
            url="b2",
            max_submissions=1
        )

        cls.exercise_in_reading_time = BaseExercise.objects.create(
            order=1,
            name="test exercise",
            course_module=cls.reading_open_course_module,
            category=cls.learning_object_category,
            url="b1",
            max_submissions=1,
        )

        cls.base_exercise_with_late_submission_allowed = BaseExercise.objects.create(
            name="test exercise with late submissions allowed",
            course_module=cls.course_module_with_late_submissions_allowed,
            category=cls.learning_object_category,
            url="b3",
        )

        cls.enrollment_exercise = BaseExercise.objects.create(
            name="test enrollment exercise",
            course_module=cls.old_course_module,
            category=cls.learning_object_category,
            url="enroll-exercise",
            max_submissions=1,
            status="enrollment",
        )

        cls.submission = Submission.objects.create(
            exercise=cls.base_exercise,
            grader=cls.grader.userprofile
        )
        cls.submission.submitters.add(cls.user.userprofile)

        cls.submission_with_two_submitters = Submission.objects.create(
            exercise=cls.base_exercise,
            grader=cls.grader.userprofile
        )
        cls.submission_with_two_submitters.submitters.add(cls.user.userprofile)
        cls.submission_with_two_submitters.submitters.add(cls.user2.userprofile)

        cls.late_submission = Submission.objects.create(
            exercise=cls.base_exercise,
            grader=cls.grader.userprofile
        )
        cls.late_submission.submission_time = cls.two_days_from_now
        cls.late_submission.submitters.add(cls.user.userprofile)

        cls.submission_when_late_allowed = Submission.objects.create(
            exercise=cls.base_exercise_with_late_submission_allowed,
            grader=cls.grader.userprofile
        )
        cls.submission_when_late_allowed.submitters.add(cls.user.userprofile)

        cls.late_submission_when_late_allowed = Submission.objects.create(
            exercise=cls.base_exercise_with_late_submission_allowed,
            grader=cls.grader.userprofile
        )
        cls.late_submission_when_late_allowed.submission_time = cls.two_days_from_now
        cls.late_submission_when_late_allowed.submitters.add(cls.user.userprofile)

        cls.late_late_submission_when_late_allowed = Submission.objects.create(
            exercise=cls.base_exercise_with_late_submission_allowed,
            grader=cls.grader.userprofile
        )
        cls.late_late_submission_when_late_allowed.submission_time = cls.three_days_from_now
        cls.late_late_submission_when_late_allowed.submitters.add(cls.user.userprofile)

        cls.course_hook = CourseHook.objects.create(
            hook_url="http://localhost/test_hook_url",
            course_instance=cls.course_instance
        )

        cls.deadline_rule_deviation = DeadlineRuleDeviation.objects.create(
            exercise=cls.exercise_with_attachment,
            submitter=cls.user.userprofile,
            granter=cls.teacher.userprofile,
            extra_seconds=24*60*60  # One day
        )


class ExerciseTest(ExerciseTestBase):
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
        self.assertFalse(self.exercise_in_reading_time.is_open())
        self.assertTrue(self.exercise_in_reading_time.is_open(self.tomorrow))

    def test_enrollment_exercise_access(self):
        # The module has closed now.
        # Enrollment exercise should be submittable even after the module closing time.
        self.assertEqual(self.enrollment_exercise.check_submission_allowed(self.user.userprofile)[0],
            BaseExercise.SUBMIT_STATUS.ALLOWED)

        # The module closed yesterday.
        self.old_course_module.closing_time = self.yesterday
        self.old_course_module.save()
        self.assertEqual(self.enrollment_exercise.check_submission_allowed(self.user.userprofile)[0],
            BaseExercise.SUBMIT_STATUS.ALLOWED)

        # The module is currently open.
        self.old_course_module.opening_time = self.yesterday
        self.old_course_module.closing_time = self.tomorrow
        self.old_course_module.save()
        self.assertEqual(self.enrollment_exercise.check_submission_allowed(self.user.userprofile)[0],
            BaseExercise.SUBMIT_STATUS.ALLOWED)

        # The module has not yet opened.
        self.old_course_module.opening_time = self.tomorrow
        self.old_course_module.closing_time = self.two_days_from_now
        self.old_course_module.save()
        self.assertEqual(self.enrollment_exercise.check_submission_allowed(self.user.userprofile)[0],
            BaseExercise.SUBMIT_STATUS.ALLOWED)

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
        self.assertFalse(self.exercise_in_reading_time.one_has_access([self.user.userprofile], self.today)[0])
        self.assertTrue(self.exercise_in_reading_time.one_has_access([self.user.userprofile], self.tomorrow)[0])

    def test_base_exercise_submission_allowed(self):
        status, alerts, _students = (
            self.base_exercise.check_submission_allowed(self.user.userprofile))
        self.assertNotEqual(status, self.base_exercise.SUBMIT_STATUS.ALLOWED)
        self.assertEqual(len(alerts['error_messages'] + alerts['warning_messages'] + alerts['info_messages']), 1)
        json.dumps(str(alerts))
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
        deviation = MaxSubmissionsRuleDeviation.objects.create( # pylint: disable=unused-variable
            exercise=self.base_exercise,
            submitter=self.user.userprofile,
            granter=self.teacher.userprofile,
            extra_submissions=3
        )
        self.assertTrue(self.base_exercise.one_has_submissions([self.user.userprofile])[0])

    def test_base_exercise_deadline_deviation(self):
        self.assertFalse(self.old_base_exercise.one_has_access([self.user.userprofile])[0])
        deviation = DeadlineRuleDeviation.objects.create( # pylint: disable=unused-variable
            exercise=self.old_base_exercise,
            submitter=self.user.userprofile,
            granter=self.teacher.userprofile,
            extra_seconds=10*24*60*60 # Ten days
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
        language = 'en'
        # the order of the parameters in the returned service url is non-deterministic,
        # so we check the parameters separately
        split_base_exercise_service_url = (
            self.base_exercise.
            _build_service_url(language, [self.user.userprofile], 1, 'exercise', 'service')
            .split("?")
        )
        split_static_exercise_service_url = (
            self.static_exercise
            ._build_service_url(language, [self.user.userprofile], 1, 'exercise', 'service')
            .split("?")
        )
        self.assertEqual("", split_base_exercise_service_url[0])
        self.assertEqual("/testServiceURL", split_static_exercise_service_url[0])
        # a quick hack to check whether the parameters are URL encoded
        self.assertFalse("/" in split_base_exercise_service_url[1] or ":" in split_base_exercise_service_url[1])
        self.assertFalse("/" in split_static_exercise_service_url[1] or ":" in split_static_exercise_service_url[1])
        # create dictionaries from the parameters and check each value.
        # Note: parse_qs changes encoding back to regular utf-8
        base_exercise_url_params = urllib.parse.parse_qs(split_base_exercise_service_url[1])
        static_exercise_url_params = urllib.parse.parse_qs(split_static_exercise_service_url[1])
        self.assertEqual(['100'], base_exercise_url_params['max_points'])
        expected = build_aplus_url("service")
        self.assertEqual(expected, base_exercise_url_params['submission_url'][0][:40])
        self.assertEqual(['50'], static_exercise_url_params['max_points'])
        self.assertEqual([expected], static_exercise_url_params['submission_url'])

    def test_static_exercise_load(self):
        request = RequestFactory().request(SERVER_NAME='localhost', SERVER_PORT='8001')
        static_exercise_page = self.static_exercise.load(request, [self.user.userprofile])
        self.assertIsInstance(static_exercise_page, ExercisePage)
        self.assertEqual("test_page_content", static_exercise_page.content)

    def test_static_exercise_grade(self):
        request = RequestFactory().request(SERVER_NAME='localhost', SERVER_PORT='8001')

        def dummy_get_response(request):
            return None

        SessionMiddleware(dummy_get_response).process_request(request)
        request.session.save()
        sub = Submission.objects.create_from_post(self.static_exercise, [self.user.userprofile], request)
        static_exercise_page = self.static_exercise.grade(request, sub)
        self.assertIsInstance(static_exercise_page, ExercisePage)
        self.assertTrue(static_exercise_page.is_accepted)
        self.assertEqual("test_submission_content", static_exercise_page.content)

    def test_exercise_upload_dir(self):
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
            granter=self.teacher.userprofile,
            extra_seconds=10*24*60*60,
            without_late_penalty=True
        )
        self.late_late_submission_when_late_allowed.set_points(5, 10)
        self.assertFalse(self.late_late_submission_when_late_allowed.late_penalty_applied)
        deviation.without_late_penalty=False
        deviation.save()
        self.late_late_submission_when_late_allowed.set_points(5, 10)
        self.assertAlmostEqual(self.late_late_submission_when_late_allowed.late_penalty_applied, 0.2)

    def test_submission_late_conversion(self):
        convert_submission_url = self.late_submission.get_url('submission-approve')
        response = self.client.get(convert_submission_url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.late_submission.late_penalty_applied is None)


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
        summary = ExercisePoints.get(self.base_exercise_with_late_submission_allowed, self.user)
        self.assertEqual(summary.submission_count, 2)
        self.assertEqual(summary.official_points, 0) # unofficial points are not shown here
        self.assertFalse(summary.graded)
        self.assertTrue(summary.unofficial)

        self.submission_when_late_allowed.set_points(5, 10)
        self.submission_when_late_allowed.set_ready()
        self.submission_when_late_allowed.save()
        self.assertEqual(self.submission_when_late_allowed.grade, 50)
        self.assertEqual(self.submission_when_late_allowed.status, Submission.STATUS.READY)
        summary = ExercisePoints.get(self.base_exercise_with_late_submission_allowed, self.user)
        self.assertEqual(summary.submission_count, 2)
        self.assertEqual(summary.official_points, 50)
        self.assertTrue(summary.graded)
        self.assertFalse(summary.unofficial)

        sub = Submission.objects.create(
            exercise=self.base_exercise_with_late_submission_allowed,
            grader=self.grader.userprofile
        )
        sub.submission_time = self.two_days_from_now + timedelta(days = 1)
        sub.save()
        sub.submitters.add(self.user.userprofile)
        sub.set_points(10, 10)
        sub.save()
        summary = ExercisePoints.get(self.base_exercise_with_late_submission_allowed, self.user)
        self.assertEqual(summary.submission_count, 2)
        self.assertEqual(summary.official_points, 50)
        self.assertTrue(summary.graded)
        self.assertFalse(summary.unofficial)

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
        self.assertEqual(
            "/Course-Url/T-00.1000_d1/test-module/b1/submissions/1/",
            self.submission.get_absolute_url()
        )
        self.assertEqual(
            "/Course-Url/T-00.1000_d1/test-module/b1/submissions/3/",
            self.late_submission.get_absolute_url()
        )

    def test_submission_upload_dir(self):
        submitted_file1 = SubmittedFile.objects.create(
            submission=self.submission,
            param_name="testParam"
        )

        submitted_file2 = SubmittedFile.objects.create(
            submission=self.submission_with_two_submitters,
            param_name="testParam2"
        )
        self.assertEqual(
            "course_instance_1/submissions/exercise_3/users_1/submission_1/test_file_name",
            build_upload_dir_for_submission_model(submitted_file1, "test_file_name")
        )
        self.assertEqual(
            "course_instance_1/submissions/exercise_3/users_1-4/submission_2/test_file_name",
            build_upload_dir_for_submission_model(submitted_file2, "test_file_name")
        )

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

    def test_exercise_staff_views(self) -> None:
        self.other_instance = CourseInstance.objects.create(
            instance_name="Another",
            starting_time=self.today,
            ending_time=self.tomorrow,
            course=self.course,
            url="another"
        )
        assessment_data = {
            "points": 0,
            "mark_as_final": False,
            "assistant_feedback": "",
            "feedback": "",
        }
        self.other_instance.add_assistant(self.grader.userprofile)
        list_submissions_url = self.base_exercise.get_submission_list_url()
        inspect_submission_url = self.submission.get_url('submission-inspect')
        response = self.client.get(list_submissions_url)
        self.assertEqual(response.status_code, 302)

        self.client.login(username="testUser", password="testPassword")
        response = self.client.get(list_submissions_url)
        self.assertEqual(response.status_code, 403)
        response = self.client.get(inspect_submission_url)
        self.assertEqual(response.status_code, 403)
        response = self.client.post(inspect_submission_url, assessment_data)
        self.assertEqual(response.status_code, 403)

        self.client.login(username="staff", password="staffPassword")
        response = self.client.get(list_submissions_url)
        self.assertEqual(response.status_code, 200)
        response = self.client.get(inspect_submission_url)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(inspect_submission_url, assessment_data)
        self.assertEqual(response.status_code, 302)

        self.client.login(username="grader", password="graderPassword")
        response = self.client.get(list_submissions_url)
        self.assertEqual(response.status_code, 200)
        response = self.client.get(inspect_submission_url)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(inspect_submission_url, assessment_data)
        self.assertEqual(response.status_code, 403)

        self.base_exercise.allow_assistant_grading = True
        self.base_exercise.save()
        response = self.client.post(inspect_submission_url, assessment_data)
        self.assertEqual(response.status_code, 302)

        self.course_instance.clear_assistants()
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
            service_url="http://grader.invalid/testServiceURL",
        )

        self.course_instance.enroll_student(self.user)
        self.client.login(username="testUser", password="testPassword")

        png_file = BytesIO(
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x05\x00\x00\x00\x05\x08\x02\x00\x00\x00\x02\r'
            b'\xb1\xb2\x00\x00\x00\x01sRGB\x00\xae\xce\x1c\xe9\x00\x00\x00\x15IDAT\x08\xd7c`\xc0\n\xfe\xff'
            b'\xff\x8f\xce\xc1"\x84\x05\x00\x00\xde\x7f\x0b\xf5<|+\x98\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        png_file.name = 'test.png'
        py_file = StringIO('print("Tekijät ja Hyyppö")')
        py_file.name = 'test.py'

        with png_file, py_file:
            response = self.client.post(exercise.get_absolute_url(), {
                "key": "value",
                "file1": png_file,
                "file2": py_file,
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

        self.assertFalse(self.base_exercise.can_show_model_solutions_to_student(self.user)) # module is open
        self.assertTrue(self.old_base_exercise.can_show_model_solutions_to_student(self.user)) # module is closed
        self.assertFalse(
            self.base_exercise_with_late_submission_allowed.can_show_model_solutions_to_student(self.user)
        ) # module is open
        self.assertFalse(base_exercise_with_late_open.can_show_model_solutions_to_student(self.user))
        self.assertTrue(base_exercise_with_late_closed.can_show_model_solutions_to_student(self.user))

        # The user has submitted alone and has no deadline extension.
        self.assertEqual(self.old_base_exercise.get_submissions_for_student(self.user.userprofile).count(), 0)
        submission1 = Submission.objects.create(
            exercise=self.old_base_exercise,
        )
        submission1.submitters.add(self.user.userprofile)
        self.assertTrue(self.old_base_exercise.can_show_model_solutions_to_student(self.user)) # module is closed
        # Add a deadline extension that is still active.
        deadline_rule_deviation_old_base_exercise = DeadlineRuleDeviation.objects.create(
            exercise=self.old_base_exercise,
            submitter=self.user.userprofile,
            granter=self.teacher.userprofile,
            extra_seconds=24*60*60, # One day
        )
        self.assertFalse(self.old_base_exercise.can_show_model_solutions_to_student(self.user))
        # Change the deadline extension so that it is not active anymore.
        self.old_course_module.closing_time = self.today - timedelta(hours=2)
        self.old_course_module.save()
        deadline_rule_deviation_old_base_exercise.delete()
        deadline_rule_deviation_old_base_exercise = DeadlineRuleDeviation.objects.create(
            exercise=self.old_base_exercise,
            submitter=self.user.userprofile,
            granter=self.teacher.userprofile,
            extra_seconds=10*60,
        )
        self.assertTrue(self.old_base_exercise.can_show_model_solutions_to_student(self.user))

        # Group submission
        submission2 = Submission.objects.create(
            exercise=base_exercise_with_late_closed,
        )
        submission2.submitters.add(self.user.userprofile, self.user2.userprofile)
        self.assertTrue(base_exercise_with_late_closed.can_show_model_solutions_to_student(self.user))
        self.assertTrue(base_exercise_with_late_closed.can_show_model_solutions_to_student(self.user2))
        # Add a deadline extension to one group member. It affects all group members.
        # Note: deadline deviations are relative to the module closing time, not the late submission deadline.
        deadline_rule_deviation_ex_late_closed = DeadlineRuleDeviation.objects.create(
            exercise=base_exercise_with_late_closed,
            submitter=self.user.userprofile,
            granter=self.teacher.userprofile,
            extra_seconds=2*24*60*60, # Two days
        )
        self.assertFalse(base_exercise_with_late_closed.can_show_model_solutions_to_student(self.user))
        self.assertFalse(base_exercise_with_late_closed.can_show_model_solutions_to_student(self.user2))
        # Change the deadline extension so that it is not active anymore.
        deadline_rule_deviation_ex_late_closed.delete()
        deadline_rule_deviation_ex_late_closed = DeadlineRuleDeviation.objects.create(
            exercise=base_exercise_with_late_closed,
            submitter=self.user.userprofile,
            granter=self.teacher.userprofile,
            extra_seconds=10*60,
        )
        self.assertTrue(base_exercise_with_late_closed.can_show_model_solutions_to_student(self.user))
        self.assertTrue(base_exercise_with_late_closed.can_show_model_solutions_to_student(self.user2))

    def test_can_be_shown_as_module_model_solution(self):
        chapter = CourseChapter.objects.create(
            name="test course chapter",
            course_module=self.course_module,
            category=self.learning_object_category,
            url="c1",
        )
        deadline_deviation_old_base_exercise = DeadlineRuleDeviation.objects.create(
            exercise=self.old_base_exercise,
            submitter=self.user.userprofile,
            granter=self.teacher.userprofile,
            extra_seconds=24*60*60, # One day
        )
        reveal_rule = RevealRule.objects.create(
            trigger=RevealRule.TRIGGER.DEADLINE,
        )
        self.old_course_module.model_answer = chapter
        self.old_course_module.model_answer_reveal_rule = reveal_rule
        self.old_course_module.save()
        self.base_exercise.parent = chapter
        self.base_exercise.save()
        self.static_exercise.parent = self.base_exercise
        self.static_exercise.save()
        # Chapter is model answer to a closed module with a deadline extension
        self.assertFalse(chapter.can_be_shown_as_module_model_solution(self.user))
        # Unrevealed chapter's child
        self.assertFalse(self.base_exercise.can_be_shown_as_module_model_solution(self.user))
        # Unrevealed chapter's grandchild
        self.assertFalse(self.static_exercise.can_be_shown_as_module_model_solution(self.user))
        self.assertTrue(chapter.can_be_shown_as_module_model_solution(self.user2))

        deadline_deviation_old_base_exercise.extra_seconds = 0
        deadline_deviation_old_base_exercise.save()
        self.assertTrue(chapter.can_be_shown_as_module_model_solution(self.user))
        self.assertTrue(self.base_exercise.can_be_shown_as_module_model_solution(self.user))
        self.assertTrue(self.static_exercise.can_be_shown_as_module_model_solution(self.user))

        self.course_instance.ending_time = self.today - timedelta(days=2)
        self.course_instance.lifesupport_time = self.yesterday
        self.course_instance.save()
        # Model answer chapters not visible after lifesupport time
        self.assertFalse(chapter.can_be_shown_as_module_model_solution(self.user))
        self.assertFalse(self.base_exercise.can_be_shown_as_module_model_solution(self.user2))

    def test_reveal_rule(self):
        reveal_rule = RevealRule.objects.create(
            trigger=RevealRule.TRIGGER.MANUAL,
        )

        reveal_state = ExerciseRevealState(self.base_exercise, self.user)
        old_reveal_state = ExerciseRevealState(self.old_base_exercise, self.user)

        self.assertFalse(reveal_rule.is_revealed(reveal_state))
        reveal_rule.currently_revealed = True
        self.assertTrue(reveal_rule.is_revealed(reveal_state))

        reveal_rule.currently_revealed = False
        reveal_rule.trigger = RevealRule.TRIGGER.IMMEDIATE
        self.assertTrue(reveal_rule.is_revealed(reveal_state))

        reveal_rule.trigger = RevealRule.TRIGGER.TIME
        self.assertFalse(reveal_rule.is_revealed(reveal_state))
        reveal_rule.time = self.today
        self.assertTrue(reveal_rule.is_revealed(reveal_state))
        reveal_rule.time = self.tomorrow
        self.assertFalse(reveal_rule.is_revealed(reveal_state))

        # Test deadline with no deviations
        for trigger in [
            RevealRule.TRIGGER.DEADLINE,
            RevealRule.TRIGGER.DEADLINE_ALL,
            RevealRule.TRIGGER.DEADLINE_OR_FULL_POINTS
        ]:
            reveal_rule.trigger = trigger
            self.assertFalse(reveal_rule.is_revealed(reveal_state))
            self.assertEqual(reveal_rule.get_reveal_time(reveal_state), self.tomorrow)
            self.assertTrue(reveal_rule.is_revealed(old_reveal_state))
            self.assertEqual(reveal_rule.get_reveal_time(old_reveal_state), self.today)
            reveal_rule.delay_minutes = 30
            self.assertFalse(reveal_rule.is_revealed(old_reveal_state))
            self.assertEqual(reveal_rule.get_reveal_time(old_reveal_state), self.today + timedelta(minutes=30))
            reveal_rule.delay_minutes = 0

        # Test deadline with deviations
        deadline_rule_deviation_old_base_exercise = DeadlineRuleDeviation.objects.create(
            exercise=self.old_base_exercise,
            submitter=self.user.userprofile,
            granter=self.teacher.userprofile,
            extra_seconds=30*60,
        )
        old_reveal_state_deviation = ExerciseRevealState(self.old_base_exercise, self.user)
        user2_old_reveal_state_deviation = ExerciseRevealState(self.old_base_exercise, self.user2)

        for trigger in [
            RevealRule.TRIGGER.DEADLINE,
            RevealRule.TRIGGER.DEADLINE_OR_FULL_POINTS
        ]:
            reveal_rule.trigger = trigger
            self.assertFalse(reveal_rule.is_revealed(old_reveal_state_deviation))
            self.assertEqual(
                reveal_rule.get_reveal_time(old_reveal_state_deviation),
                self.today + timedelta(minutes=30)
            )
            self.assertTrue(reveal_rule.is_revealed(user2_old_reveal_state_deviation))
            self.assertEqual(reveal_rule.get_reveal_time(user2_old_reveal_state_deviation), self.today)

        reveal_rule.trigger = RevealRule.TRIGGER.DEADLINE_ALL
        self.assertFalse(reveal_rule.is_revealed(user2_old_reveal_state_deviation))
        self.assertEqual(
            reveal_rule.get_reveal_time(user2_old_reveal_state_deviation),
            self.today + timedelta(minutes=30)
        )

        deadline_rule_deviation_old_base_exercise.delete()

    def test_reveal_rule_max_submissions(self):
        reveal_rule = RevealRule.objects.create(
            trigger=RevealRule.TRIGGER.MANUAL,
        )

        completion_test_base_exercise = BaseExercise.objects.create(
            name="completion test exercise",
            course_module=self.course_module,
            category=self.learning_object_category,
            url="bcompletion",
            max_submissions=2,
            max_points=10,
        )

        reveal_rule.trigger = RevealRule.TRIGGER.COMPLETION
        self.assertFalse(reveal_rule.is_revealed(ExerciseRevealState(completion_test_base_exercise, self.user)))
        submission = Submission.objects.create(
            exercise=completion_test_base_exercise,
            status=Submission.STATUS.READY,
            grade=0,
        )
        submission.submitters.add(self.user.userprofile)
        self.assertFalse(reveal_rule.is_revealed(ExerciseRevealState(completion_test_base_exercise, self.user)))
        submission2 = Submission.objects.create(
            exercise=completion_test_base_exercise,
            status=Submission.STATUS.READY,
            grade=0,
        )
        submission2.submitters.add(self.user.userprofile)
        self.assertTrue(reveal_rule.is_revealed(ExerciseRevealState(completion_test_base_exercise, self.user)))
        submission.delete()
        submission2.delete()

    def test_reveal_rule_full_points(self):
        reveal_rule = RevealRule.objects.create(
            trigger=RevealRule.TRIGGER.MANUAL,
        )

        completion_test_base_exercise = BaseExercise.objects.create(
            name="completion test exercise",
            course_module=self.course_module,
            category=self.learning_object_category,
            url="bcompletion",
            max_submissions=2,
            max_points=10,
        )

        for trigger in [
            RevealRule.TRIGGER.COMPLETION,
            RevealRule.TRIGGER.DEADLINE_OR_FULL_POINTS
        ]:
            if trigger == RevealRule.TRIGGER.DEADLINE_OR_FULL_POINTS:
                # The deadline cant be passed for DEADLINE_OR_FULL_POINTS or the points are always revealed
                self.course_module.closing_time=self.tomorrow
                self.course_module.save()

            else:
                # The deadline is purposefully passed for COMPLETION trigger to make sure that it doesn't cause the
                # points to be revealed
                self.course_module.closing_time=self.yesterday
                self.course_module.save()
            reveal_rule.trigger = trigger
            reveal_rule.save()
            self.assertFalse(reveal_rule.is_revealed(ExerciseRevealState(completion_test_base_exercise, self.user)))
            self.assertFalse(reveal_rule.is_revealed(ExerciseRevealState(completion_test_base_exercise, self.user2)))
            submission = Submission.objects.create(
                exercise=completion_test_base_exercise,
                status=Submission.STATUS.READY,
                grade=10,
            )
            submission.submitters.add(self.user.userprofile)
            self.assertTrue(reveal_rule.is_revealed(ExerciseRevealState(completion_test_base_exercise, self.user)))
            self.assertFalse(reveal_rule.is_revealed(ExerciseRevealState(completion_test_base_exercise, self.user2)))
            submission.submitters.add(self.user2.userprofile)
            self.assertTrue(reveal_rule.is_revealed(ExerciseRevealState(completion_test_base_exercise, self.user)))
            self.assertTrue(reveal_rule.is_revealed(ExerciseRevealState(completion_test_base_exercise, self.user2)))
            submission.delete()

        completion_test_base_exercise.delete()

    def test_module_reveal_state(self):
        course_module_chapter = CourseChapter.objects.create(
            name="test course chapter",
            course_module=self.course_module,
            category=self.learning_object_category,
            url="c1",
        )
        optional_exercise = BaseExercise.objects.create(
            order=4,
            name="test exercise 4",
            course_module=self.course_module,
            category=self.learning_object_category,
            url="b4",
            max_submissions=0,
            max_points=1,
        )
        self.base_exercise.parent = course_module_chapter
        self.base_exercise.max_points = 5
        # max submissions 1
        self.base_exercise.save()
        self.static_exercise.parent = course_module_chapter
        self.static_exercise.max_submissions = 2
        # max points 50
        self.static_exercise.save()
        self.exercise_with_attachment.max_submissions = 1
        # max points 50
        self.exercise_with_attachment.save()

        DeadlineRuleDeviation.objects.create(
            exercise=self.old_base_exercise,
            submitter=self.user.userprofile,
            granter=self.teacher.userprofile,
            extra_seconds=3*24*60*60, # Three days
        ) # this should have not effect on the module reveal state

        user_reveal_state = ModuleRevealState(self.course_module, self.user)
        self.assertEqual(len(user_reveal_state.exercises), 4)
        self.assertEqual(user_reveal_state.get_deadline(), self.two_days_from_now) # User has a deadline deviation
        user2_reveal_state = ModuleRevealState(self.course_module, self.user2)
        self.assertEqual(user2_reveal_state.get_deadline(), self.tomorrow) # User2 has no deadline deviation
        self.assertEqual(user2_reveal_state.get_latest_deadline(), self.two_days_from_now)
        self.assertEqual(user_reveal_state.get_latest_deadline(), self.two_days_from_now)

        user_reveal_state_with_late_submissions = ModuleRevealState(
            self.course_module_with_late_submissions_allowed, self.user
        )
        self.assertEqual(user_reveal_state_with_late_submissions.get_deadline(), self.two_days_from_now)

        Submission.objects.all().delete()
        for submission_data in [
            {
                'exercise': self.base_exercise,
                'grade': 5,
                'status': Submission.STATUS.READY,
            },
            {
                'exercise': optional_exercise,
                'grade': 1,
                'status': Submission.STATUS.READY,
            }, # Should have no effect on submission count, since max_submissions is 0
            {
                'exercise': self.static_exercise,
                'grade': 10,
                'status': Submission.STATUS.READY,
            },
            {
                'exercise': self.static_exercise,
                'grade': 40,
                'status': Submission.STATUS.READY,
            },
            {
                'exercise': self.static_exercise,
                'grade': 50,
                'status': Submission.STATUS.UNOFFICIAL,
            }, # Should have no effect
            {
                'exercise': self.old_base_exercise,
                'grade': 10,
                'status': Submission.STATUS.READY,
            }, # Should have no effect
        ]:
            submission = Submission.objects.create(**submission_data)
            submission.submitters.add(self.user.userprofile)

        user_reveal_state = ModuleRevealState(self.course_module, self.user)
        self.assertEqual(user_reveal_state.get_points(), 46)
        self.assertEqual(user_reveal_state.get_max_points(), 106)
        self.assertEqual(user_reveal_state.get_submissions(), 3)
        self.assertEqual(user_reveal_state.get_max_submissions(), 4)


    def test_annotate_submitter_points(self):
        points_test_base_exercise_1 = BaseExercise.objects.create(
            name="points test base exercise 1",
            course_module=self.course_module,
            category=self.learning_object_category,
            url="bsubmitterpoints1",
            max_submissions=3,
            max_points=10,
            grading_mode=BaseExercise.GRADING_MODE.BEST,
        )
        points_test_base_exercise_2 = BaseExercise.objects.create(
            name="points test base exercise 2",
            course_module=self.course_module,
            category=self.learning_object_category,
            url="bsubmitterpoints2",
            max_submissions=3,
            max_points=10,
            grading_mode=BaseExercise.GRADING_MODE.LAST,
        )

        # Create test submissions, so that the final points:
        # - for user 1 exercise 1 should be 5
        # - for user 1 exercise 2 should be 6
        # - for user 2 exercise 1 should be 0
        # - for user 2 exercise 2 should be 1
        for submission_data in [
            {
                'exercise': points_test_base_exercise_1,
                'grade': 5,
                'status': Submission.STATUS.READY,
                'force_exercise_points': False
            },
            {
                'exercise': points_test_base_exercise_1,
                'grade': 10,
                'status': Submission.STATUS.REJECTED,
                'force_exercise_points': False
            },
            {
                'exercise': points_test_base_exercise_1,
                'grade': 1,
                'status': Submission.STATUS.READY,
                'force_exercise_points': False
            },
            {
                'exercise': points_test_base_exercise_2,
                'grade': 6,
                'status': Submission.STATUS.READY,
                'force_exercise_points': True
            },
            {
                'exercise': points_test_base_exercise_2,
                'grade': 10,
                'status': Submission.STATUS.READY,
                'force_exercise_points': False
            },
            {
                'exercise': points_test_base_exercise_2,
                'grade': 0,
                'status': Submission.STATUS.READY,
                'force_exercise_points': False
            },
        ]:
            submission = Submission.objects.create(**submission_data)
            submission.submitters.add(self.user.userprofile)
        for submission_data in [
            {
                'exercise': points_test_base_exercise_1,
                'grade': 1,
                'status': Submission.STATUS.INITIALIZED,
                'force_exercise_points': False
            },
            {
                'exercise': points_test_base_exercise_1,
                'grade': 1,
                'status': Submission.STATUS.INITIALIZED,
                'force_exercise_points': False
            },
            {
                'exercise': points_test_base_exercise_1,
                'grade': 1,
                'status': Submission.STATUS.INITIALIZED,
                'force_exercise_points': False
            },
            {
                'exercise': points_test_base_exercise_2,
                'grade': 2,
                'status': Submission.STATUS.READY,
                'force_exercise_points': False
            },
            {
                'exercise': points_test_base_exercise_2,
                'grade': 1,
                'status': Submission.STATUS.READY,
                'force_exercise_points': False
            },
            {
                'exercise': points_test_base_exercise_2,
                'grade': 0,
                'status': Submission.STATUS.UNOFFICIAL,
                'force_exercise_points': False
            },
        ]:
            submission = Submission.objects.create(**submission_data)
            submission.submitters.add(self.user2.userprofile)

        points_rows = (
            Submission.objects
            .filter(exercise__in=(points_test_base_exercise_1, points_test_base_exercise_2))
            .values('submitters__user_id', 'exercise_id')
            .annotate_submitter_points('total')
            .order_by()
        )

        # There should be 4 rows (2 users * 2 exercises)
        self.assertEqual(len(points_rows), 4)

        # Collect the results into a dict and test that they match the expected
        # values. This also checks that all expected results were returned,
        # otherwise a KeyError is raised.
        points_dict = {}
        for row in points_rows:
            points_dict[(row['submitters__user_id'], row['exercise_id'])] = row['total']
        self.assertEqual(points_dict[(self.user.id, points_test_base_exercise_1.id)], 5)
        self.assertEqual(points_dict[(self.user.id, points_test_base_exercise_2.id)], 6)
        self.assertEqual(points_dict[(self.user2.id, points_test_base_exercise_1.id)], 0)
        self.assertEqual(points_dict[(self.user2.id, points_test_base_exercise_2.id)], 1)

        # Test with one exercise and submitter, and include_unofficial=True.
        points_rows_unofficial = (
            Submission.objects
            .filter(exercise=points_test_base_exercise_2, submitters=self.user2.userprofile)
            .values('submitters__user_id', 'exercise_id')
            .annotate_submitter_points('total', include_unofficial=True)
            .order_by()
        )
        self.assertEqual(len(points_rows_unofficial), 1)
        self.assertEqual(points_rows_unofficial[0]['total'], 0)

        # Test with no revealed exercises (all points should be 0).
        points_rows_unrevealed = (
            Submission.objects
            .filter(exercise__in=(points_test_base_exercise_1, points_test_base_exercise_2))
            .values('submitters__user_id', 'exercise_id')
            .annotate_submitter_points('total', revealed_ids=())
            .order_by()
        )
        self.assertEqual(len(points_rows_unrevealed), 4)
        for row in points_rows_unrevealed:
            self.assertEqual(row['total'], 0)

        points_test_base_exercise_1.delete()
        points_test_base_exercise_2.delete()

    def test_submission_draft(self):
        # Initial state, there are no drafts
        draft1 = self.base_exercise.get_submission_draft(self.user.userprofile)
        self.assertIsNone(draft1)
        draft2 = self.base_exercise.get_submission_draft(self.user2.userprofile)
        self.assertIsNone(draft2)

        # User 1 creates a draft
        self.base_exercise.set_submission_draft(self.user.userprofile, [["key", "value1"]])
        self.assertEqual(len(self.base_exercise.submission_drafts.all()), 1)
        draft1 = self.base_exercise.get_submission_draft(self.user.userprofile)
        self.assertEqual(draft1.submission_data, [["key", "value1"]])
        draft2 = self.base_exercise.get_submission_draft(self.user2.userprofile)
        self.assertIsNone(draft2)

        # User 2 creates a draft
        self.base_exercise.set_submission_draft(self.user2.userprofile, [["key", "value2"]])
        self.assertEqual(len(self.base_exercise.submission_drafts.all()), 2)
        draft1 = self.base_exercise.get_submission_draft(self.user.userprofile)
        self.assertEqual(draft1.submission_data, [["key", "value1"]])
        draft2 = self.base_exercise.get_submission_draft(self.user2.userprofile)
        self.assertEqual(draft2.submission_data, [["key", "value2"]])

        # User 1 draft is updated
        self.base_exercise.set_submission_draft(self.user.userprofile, [["key", "value3"]])
        self.assertEqual(len(self.base_exercise.submission_drafts.all()), 2) # No new draft should be created
        draft1 = self.base_exercise.get_submission_draft(self.user.userprofile)
        self.assertEqual(draft1.submission_data, [["key", "value3"]])
        draft2 = self.base_exercise.get_submission_draft(self.user2.userprofile)
        self.assertEqual(draft2.submission_data, [["key", "value2"]])

        # User 1 draft is deactvated
        self.base_exercise.unset_submission_draft(self.user.userprofile)
        self.assertEqual(len(self.base_exercise.submission_drafts.all()), 2) # The draft still exists but is inactive
        draft1 = self.base_exercise.get_submission_draft(self.user.userprofile)
        self.assertIsNone(draft1)
        draft2 = self.base_exercise.get_submission_draft(self.user2.userprofile)
        self.assertEqual(draft2.submission_data, [["key", "value2"]])

        # User 1 creates a new draft
        self.base_exercise.set_submission_draft(self.user.userprofile, [["key", "value4"]])
        self.assertEqual(len(self.base_exercise.submission_drafts.all()), 2) # The original draft should be reused
        draft1 = self.base_exercise.get_submission_draft(self.user.userprofile)
        self.assertEqual(draft1.submission_data, [["key", "value4"]])
        draft2 = self.base_exercise.get_submission_draft(self.user2.userprofile)
        self.assertEqual(draft2.submission_data, [["key", "value2"]])

    def test_enrollment_questionaire_opening_time(self):
        course_module = self.enrollment_exercise.course_module
        course_module.closing_time = self.two_days_from_now

        # Course and enrollment are open.
        self.course_instance.starting_time = self.yesterday
        self.course_instance.enrollment_starting_time = self.yesterday
        self.course_instance.save()
        course_module.opening_time = self.yesterday
        course_module.save()
        self.assertEqual(
            self.enrollment_exercise.check_submission_allowed(self.user.userprofile)[0],
            BaseExercise.SUBMIT_STATUS.ALLOWED,
        )

        # Only enrollment isn't open.
        self.course_instance.enrollment_starting_time = self.tomorrow
        self.course_instance.save()
        self.assertEqual(
            self.enrollment_exercise.check_submission_allowed(self.user.userprofile)[0],
            BaseExercise.SUBMIT_STATUS.CANNOT_ENROLL,
        )

        # Enrollment is open but the module is not.
        self.course_instance.enrollment_starting_time = self.yesterday
        self.course_instance.save()
        course_module.starting_time = self.tomorrow
        course_module.save()
        self.assertEqual(
            self.enrollment_exercise.check_submission_allowed(self.user.userprofile)[0],
            BaseExercise.SUBMIT_STATUS.ALLOWED,
        )

        # Course isn't open but enrollment is. Module is open.
        self.course_instance.enrollment_starting_time = self.yesterday
        self.course_instance.starting_time = self.tomorrow
        self.course_instance.save()
        course_module.starting_time = self.yesterday
        course_module.save()
        self.assertEqual(
            self.enrollment_exercise.check_submission_allowed(self.user.userprofile)[0],
            BaseExercise.SUBMIT_STATUS.ALLOWED,
        )

        # Course isn't open but enrollment is. Module is closed.
        self.course_instance.enrollment_starting_time = self.yesterday
        self.course_instance.starting_time = self.tomorrow
        self.course_instance.save()
        course_module.starting_time = self.tomorrow
        course_module.save()
        self.assertEqual(
            self.enrollment_exercise.check_submission_allowed(self.user.userprofile)[0],
            BaseExercise.SUBMIT_STATUS.ALLOWED,
        )

        # Course, enrollment and module are closed.
        self.course_instance.enrollment_starting_time = self.tomorrow
        self.course_instance.starting_time = self.tomorrow
        self.course_instance.save()
        course_module.starting_time = self.tomorrow
        course_module.save()
        self.assertEqual(
            self.enrollment_exercise.check_submission_allowed(self.user.userprofile)[0],
            BaseExercise.SUBMIT_STATUS.CANNOT_ENROLL,
        )

        # Course and enrollment are closed. Module is open.
        self.course_instance.enrollment_starting_time = self.tomorrow
        self.course_instance.starting_time = self.tomorrow
        self.course_instance.save()
        course_module.starting_time = self.yesterday
        course_module.save()
        self.assertEqual(
            self.enrollment_exercise.check_submission_allowed(self.user.userprofile)[0],
            BaseExercise.SUBMIT_STATUS.CANNOT_ENROLL,
        )

    def test_next_unassessed_submitter_view(self):
        # parses the user ID from the URL response of NextUnassessedSubmitterView for convenience. If the URL format is
        # different (e.g. redirect when all have been graded) return just the url
        def get_url_user_id():
            response = self.client.get(
                f"{exercise.get_absolute_url()}submitters/next-unassessed/")
            try:
                return int(response.url.split('/submissions/')[1].split('/inspect/')[0])
            except Exception:
                return response.url

        def create_submission(user, submission_time):
            submission = Submission.objects.create(
                exercise=exercise,
            )
            submission.submitters.add(user)
            submission.submission_time = submission_time
            submission.save()
            return submission

        self.client.login(username="staff", password="staffPassword")

        exercise = BaseExercise.objects.create(
            order=10,
            name="Unassessed Exercise Submitter View",
            course_module=self.course_module,
            category=self.learning_object_category,
            url="unassessed",
            max_submissions=1,
        )
        exercise.save()

        user_submission = create_submission(self.user.userprofile, self.yesterday)

        user2_submission = create_submission(self.user2.userprofile, self.today)

        # user submission day before user2
        self.assertEqual(user_submission.id, get_url_user_id())

        user2_submission.submission_time = self.yesterday - timedelta(days=1)
        user2_submission.save()

        # now user2 submission is earlier
        self.assertEqual(user2_submission.id, get_url_user_id())

        # we should now expect to get user1's submission first since user2s earlier submission has been graded
        user2_submission.grader = self.teacher.userprofile
        user2_submission.save()
        self.assertEqual(user_submission.id, get_url_user_id())

        # remove grader for further tests
        user2_submission.grader = None
        user2_submission.save()

        # create a submission for user so the newest submission was made by user again and not user2
        user_earlier_submission = create_submission(self.user.userprofile, self.yesterday - timedelta(days=2))

        self.assertEqual(user_submission.id, get_url_user_id())

        user2_other_exercise_submission  = Submission.objects.create(
            exercise=self.exercise_with_attachment
        )
        user2_other_exercise_submission.submitters.add(self.user2.userprofile)
        user2_other_exercise_submission.submission_time = self.yesterday - timedelta(days=3)
        user2_other_exercise_submission.save()

        # an even earlier submission in another exercise doesn't matter
        self.assertEqual(user_submission.id, get_url_user_id())

        # we should now expect user2's submission to be shown because user1's latest submission has been graded
        user_earlier_submission.grader = self.teacher.userprofile
        user_earlier_submission.save()
        self.assertEqual(user2_submission.id, get_url_user_id())

        # grading in an older submission (not latest) should also mean user1 is skipped
        user_earlier_submission.grader = self.teacher.userprofile
        user_earlier_submission.save()
        user_submission.grader = None
        user_submission.save()
        self.assertEqual(user2_submission.id, get_url_user_id())

        # everything has been graded (we should get the submissions list)
        user2_submission.grader = self.teacher.userprofile
        user2_submission.save()
        self.assertEqual(exercise.get_submission_list_url(), get_url_user_id())
