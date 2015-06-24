from datetime import datetime, timedelta
import urllib

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.test.client import RequestFactory
from django.utils import timezone
from django.utils.datastructures import MultiValueDict

from course.models import Course, CourseInstance, CourseHook
from exercise.models import CourseModule, LearningObjectCategory, LearningObject, \
    BaseExercise, StaticExercise, ExerciseWithAttachment, Submission, SubmittedFile, \
    DeadlineRuleDeviation
from exercise.presentation.summary import UserCourseSummary
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
            website="http://www.example.com",
            starting_time=self.today,
            ending_time=self.tomorrow,
            course=self.course,
            url="T-00.1000_d1"
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
        self.hidden_learning_object_category.hidden_to.add(self.user.userprofile)

        self.learning_object = LearningObject.objects.create(
            name="test learning object",
            course_module=self.course_module,
            category=self.learning_object_category
        )

        self.broken_learning_object = LearningObject.objects.create(
            name="test learning object",
            course_module=self.course_module_with_late_submissions_allowed,
            category=self.learning_object_category
        )

        self.base_exercise = BaseExercise.objects.create(
            name="test exercise",
            course_module=self.course_module,
            category=self.learning_object_category,
            max_submissions=1
        )

        self.static_exercise = StaticExercise.objects.create(
            name="test exercise 2",
            course_module=self.course_module,
            category=self.learning_object_category,
            max_points=50,
            points_to_pass=50,
            service_url="/testServiceURL",
            exercise_page_content="test_page_content",
            submission_page_content="test_submission_content"
        )

        self.exercise_with_attachment = ExerciseWithAttachment.objects.create(
            name="test exercise 3",
            course_module=self.course_module,
            category=self.learning_object_category,
            max_points=50,
            points_to_pass=50,
            max_submissions=0,
            files_to_submit="test1.txt|test2.txt|img.png",
            instructions="test_instructions"
        )

        self.old_base_exercise = BaseExercise.objects.create(
            name="test exercise",
            course_module=self.old_course_module,
            category=self.learning_object_category,
            max_submissions=1
        )

        self.base_exercise_with_late_submission_allowed = BaseExercise.objects.create(
            name="test exercise with late submissions allowed",
            course_module=self.course_module_with_late_submissions_allowed,
            category=self.learning_object_category
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
            hook_url="test_hook_url",
            course_instance=self.course_instance
        )

        self.deadline_rule_deviation = DeadlineRuleDeviation.objects.create(
            exercise=self.exercise_with_attachment,
            submitter=self.user.userprofile,
            extra_minutes=1440  # One day
        )

        self.submitted_file1 = SubmittedFile.objects.create(
            submission=self.submission,
            param_name="testParam"
        )

        self.submitted_file2 = SubmittedFile.objects.create(
            submission=self.submission_with_two_submitters,
            param_name="testParam2"
        )

    def test_course_module_exercises_list(self):
        exercises = self.course_module.get_exercises()
        exercises_with_late_submission_allowed = self.course_module_with_late_submissions_allowed.get_exercises()
        self.assertEquals(3, len(exercises))
        self.assertEquals("test exercise", exercises[0].name)
        self.assertEquals("test exercise 2", exercises[1].name)
        self.assertEquals("test exercise 3", exercises[2].name)
        self.assertEquals(1, len(exercises_with_late_submission_allowed))
        self.assertEquals("test exercise with late submissions allowed", exercises_with_late_submission_allowed[0].name)

    def test_course_module_late_submission_point_worth(self):
        self.assertEquals(0, self.course_module.get_late_submission_point_worth())
        self.assertEquals(80, self.course_module_with_late_submissions_allowed.get_late_submission_point_worth())

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

    def test_course_module_breadcrumb(self):
        breadcrumb = self.course_module.get_breadcrumb()
        self.assertEqual(2, len(breadcrumb))
        self.assertEqual(2, len(breadcrumb[1]))
        self.assertEqual("test module", breadcrumb[1][0])
        self.assertEqual("/Course-Url/T-00.1000_d1/test-module/", breadcrumb[1][1])

    def test_learning_object_category_unicode_string(self):
        self.assertEqual("test category / 123456 test course: Fall 2011 day 1", str(self.learning_object_category))
        self.assertEqual("hidden category / 123456 test course: Fall 2011 day 1", str(self.hidden_learning_object_category))

    def test_learning_object_category_exercises(self):
        self.assertEquals(5, len(self.learning_object_category.get_exercises()))
        self.assertEquals(0, len(self.hidden_learning_object_category.get_exercises()))

    def test_learning_object_category_max_points(self):
        self.assertEquals(400, self.learning_object_category.get_maximum_points())
        self.assertEquals(0, self.hidden_learning_object_category.get_maximum_points())

    def test_learning_object_category_required_percentage(self):
        self.assertEquals(1, self.learning_object_category.get_required_percentage())
        self.assertEquals(0, self.hidden_learning_object_category.get_required_percentage())

    def test_learning_object_category_hiding(self):
        self.assertFalse(self.learning_object_category.is_hidden_to(self.user.userprofile))
        self.assertFalse(self.learning_object_category.is_hidden_to(self.grader.userprofile))
        self.assertTrue(self.hidden_learning_object_category.is_hidden_to(self.user.userprofile))
        self.assertFalse(self.hidden_learning_object_category.is_hidden_to(self.grader.userprofile))

        self.hidden_learning_object_category.set_hidden_to(self.user.userprofile, False)
        self.hidden_learning_object_category.set_hidden_to(self.grader.userprofile)

        self.assertFalse(self.hidden_learning_object_category.is_hidden_to(self.user.userprofile))
        self.assertTrue(self.hidden_learning_object_category.is_hidden_to(self.grader.userprofile))

        self.hidden_learning_object_category.set_hidden_to(self.user.userprofile, True)
        self.hidden_learning_object_category.set_hidden_to(self.grader.userprofile, False)

        self.assertTrue(self.hidden_learning_object_category.is_hidden_to(self.user.userprofile))
        self.assertFalse(self.hidden_learning_object_category.is_hidden_to(self.grader.userprofile))

    def test_learning_object_clean(self):
        try:
            self.learning_object.clean()
        except ValidationError:
            self.fail()
        self.assertRaises(ValidationError, self.broken_learning_object.clean())

    def test_learning_object_course_instance(self):
        self.assertEqual(self.course_instance, self.learning_object.course_instance)
        self.assertEqual(self.course_instance, self.broken_learning_object.course_instance)

    def test_base_exercise_one_has_submissions(self):
        self.assertFalse(self.base_exercise.one_has_submissions([self.user.userprofile]))
        self.assertTrue(self.static_exercise.one_has_submissions([self.user.userprofile]))
        self.assertTrue(self.exercise_with_attachment.one_has_submissions([self.user.userprofile]))

    def test_base_exercise_max_submissions(self):
        self.assertEqual(1, self.base_exercise.max_submissions_for_student(self.user.userprofile))
        self.assertEqual(10, self.static_exercise.max_submissions_for_student(self.user.userprofile))
        self.assertEqual(0, self.exercise_with_attachment.max_submissions_for_student(self.user.userprofile))

    def test_base_exercise_submissions_for_student(self):
        self.assertEqual(3, len(self.base_exercise.get_submissions_for_student(self.user.userprofile)))
        self.assertEqual(0, len(self.static_exercise.get_submissions_for_student(self.user.userprofile)))
        self.assertEqual(0, len(self.exercise_with_attachment.get_submissions_for_student(self.user.userprofile)))

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
        self.assertTrue(self.base_exercise.one_has_access([self.user.userprofile]))
        self.assertTrue(self.static_exercise.one_has_access([self.user.userprofile]))
        self.assertTrue(self.exercise_with_attachment.one_has_access([self.user.userprofile]))
        self.assertFalse(self.old_base_exercise.one_has_access([self.user.userprofile]))
        self.assertFalse(self.base_exercise.one_has_access([self.user.userprofile], self.yesterday))
        self.assertFalse(self.static_exercise.one_has_access([self.user.userprofile], self.yesterday))
        self.assertFalse(self.exercise_with_attachment.one_has_access([self.user.userprofile], self.yesterday))
        self.assertTrue(self.old_base_exercise.one_has_access([self.user.userprofile], self.yesterday))
        self.assertTrue(self.base_exercise.one_has_access([self.user.userprofile], self.tomorrow))
        self.assertTrue(self.static_exercise.one_has_access([self.user.userprofile], self.tomorrow))
        self.assertTrue(self.exercise_with_attachment.one_has_access([self.user.userprofile], self.tomorrow))
        self.assertFalse(self.old_base_exercise.one_has_access([self.user.userprofile], self.tomorrow))

    def test_base_exercise_submission_allowed(self):
        self.assertFalse(self.base_exercise.is_submission_allowed([self.user.userprofile])[0])
        self.assertTrue(self.static_exercise.is_submission_allowed([self.user.userprofile])[0])
        self.assertTrue(self.exercise_with_attachment.is_submission_allowed([self.user.userprofile])[0])
        self.assertFalse(self.old_base_exercise.is_submission_allowed([self.user.userprofile])[0])
        self.assertFalse(self.base_exercise.is_submission_allowed([self.user.userprofile, self.grader.userprofile])[0])
        self.assertFalse(self.static_exercise.is_submission_allowed([self.user.userprofile, self.grader.userprofile])[0])
        self.assertFalse(self.exercise_with_attachment.is_submission_allowed([self.user.userprofile, self.grader.userprofile])[0])
        self.assertFalse(self.old_base_exercise.is_submission_allowed([self.user.userprofile, self.grader.userprofile])[0])
        self.assertTrue(self.base_exercise.is_submission_allowed([self.grader.userprofile])[0])
        self.assertTrue(self.static_exercise.is_submission_allowed([self.grader.userprofile])[0])
        self.assertTrue(self.exercise_with_attachment.is_submission_allowed([self.grader.userprofile])[0])
        self.assertTrue(self.old_base_exercise.is_submission_allowed([self.grader.userprofile])[0])

    def test_base_exercise_total_submission_count(self):
        self.assertEqual(self.base_exercise.get_total_submitter_count(), 2)
        self.assertEqual(self.static_exercise.get_total_submitter_count(), 0)
        self.assertEqual(self.exercise_with_attachment.get_total_submitter_count(), 0)

    def test_base_exercise_unicode_string(self):
        self.assertEqual("test exercise", str(self.base_exercise))
        self.assertEqual("test exercise 2", str(self.static_exercise))
        self.assertEqual("test exercise 3", str(self.exercise_with_attachment))

    def test_base_exercise_absolute_url(self):
        self.assertEqual("/Course-Url/T-00.1000_d1/exercises/3/", self.base_exercise.get_absolute_url())
        self.assertEqual("/Course-Url/T-00.1000_d1/exercises/4/", self.static_exercise.get_absolute_url())
        self.assertEqual("/Course-Url/T-00.1000_d1/exercises/5/", self.exercise_with_attachment.get_absolute_url())

    def test_base_exercise_breadcrumb(self):
        self.assertEqual([('123456 test course', '/Course-Url/T-00.1000_d1/'), ('test module', '/Course-Url/T-00.1000_d1/test-module/'), ('test exercise', '/Course-Url/T-00.1000_d1/exercises/3/')],
                         self.base_exercise.get_breadcrumb())
        self.assertEqual([('123456 test course', '/Course-Url/T-00.1000_d1/'), ('test module', '/Course-Url/T-00.1000_d1/test-module/'), ('test exercise 2', '/Course-Url/T-00.1000_d1/exercises/4/')],
                         self.static_exercise.get_breadcrumb())
        self.assertEqual([('123456 test course', '/Course-Url/T-00.1000_d1/'), ('test module', '/Course-Url/T-00.1000_d1/test-module/'), ('test exercise 3', '/Course-Url/T-00.1000_d1/exercises/5/')],
                         self.exercise_with_attachment.get_breadcrumb())

    def test_base_exercise_async_url(self):
        request = RequestFactory().request(SERVER_NAME='localhost', SERVER_PORT='8001')
        # the order of the parameters in the returned service url is non-deterministic, so we check the parameters separately
        split_base_exercise_service_url = self.base_exercise._build_service_url(request, 'service').split("?") 
        split_static_exercise_service_url = self.static_exercise._build_service_url(request, 'service').split("?")
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
        self.assertEqual("exercise_attachments/exercise_5/test_file_name",
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

    def test_deadline_rule_deviation_extra_time(self):
        self.assertEqual(timedelta(days=1), self.deadline_rule_deviation.get_extra_time())

    def test_deadline_rule_deviation_new_deadline(self):
        self.assertEqual(self.two_days_from_now, self.deadline_rule_deviation.get_new_deadline())

    def test_deadline_rule_deviation_normal_deadline(self):
        self.assertEqual(self.tomorrow, self.deadline_rule_deviation.get_normal_deadline())

    def test_submission_files(self):
        self.assertEqual(1, len(self.submission.files.all()))
        self.submission.add_files(MultiValueDict({
            "key1": ["test_file1.txt", "test_file2.txt"],
            "key2": ["test_image.png", "test_audio.wav", "test_pdf.pdf"]
        }))
        self.assertEqual(6, len(self.submission.files.all()))

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
        self.assertTrue(self.late_submission.late_penalty_applied)
        self.assertFalse(self.submission_when_late_allowed.late_penalty_applied)
        self.assertTrue(self.late_submission_when_late_allowed.late_penalty_applied)
        self.assertTrue(self.late_late_submission_when_late_allowed.late_penalty_applied)

    def test_submission_unicode_string(self):
        self.assertEqual("1", str(self.submission))
        self.assertEqual("2", str(self.submission_with_two_submitters))
        self.assertEqual("3", str(self.late_submission))
        self.assertEqual("4", str(self.submission_when_late_allowed))
        self.assertEqual("5", str(self.late_submission_when_late_allowed))
        self.assertEqual("6", str(self.late_late_submission_when_late_allowed))

    def test_submission_status(self):
        self.assertEqual("initialized", self.submission.status)
        self.assertFalse(self.submission.is_graded())
        self.submission.set_error()
        self.assertEqual("error", self.submission.status)
        self.assertFalse(self.submission.is_graded())
        self.submission.set_waiting()
        self.assertEqual("waiting", self.submission.status)
        self.assertFalse(self.submission.is_graded())
        self.submission.set_error()
        self.assertEqual("error", self.submission.status)
        self.assertFalse(self.submission.is_graded())
        self.assertEqual(None, self.submission.grading_time)
        self.submission.set_ready()
        self.assertIsInstance(self.submission.grading_time, datetime)
        self.assertEqual("ready", self.submission.status)
        self.assertTrue(self.submission.is_graded())

    def test_submission_absolute_url(self):
        self.assertEqual("/Course-Url/T-00.1000_d1/exercises/3/submissions/1/", self.submission.get_absolute_url())
        self.assertEqual("/Course-Url/T-00.1000_d1/exercises/3/submissions/3/", self.late_submission.get_absolute_url())

    def test_submission_breadcrumb(self):
        breadcrumb = self.submission.get_breadcrumb()
        self.assertEqual(4, len(breadcrumb))
        self.assertEqual(('123456 test course', '/Course-Url/T-00.1000_d1/'), breadcrumb[0])
        self.assertEqual(('test module', '/Course-Url/T-00.1000_d1/test-module/'), breadcrumb[1])
        self.assertEqual(('test exercise', '/Course-Url/T-00.1000_d1/exercises/3/'), breadcrumb[2])
        self.assertEqual(2, len(breadcrumb[3]))
        self.assertEqual('/Course-Url/T-00.1000_d1/exercises/3/submissions/1/', breadcrumb[3][1])
        breadcrumb = self.late_submission.get_breadcrumb()
        self.assertEqual(4, len(breadcrumb))
        self.assertEqual(('123456 test course', '/Course-Url/T-00.1000_d1/'), breadcrumb[0])
        self.assertEqual(('test module', '/Course-Url/T-00.1000_d1/test-module/'), breadcrumb[1])
        self.assertEqual(('test exercise', '/Course-Url/T-00.1000_d1/exercises/3/'), breadcrumb[2])
        self.assertEqual(2, len(breadcrumb[3]))
        self.assertEqual('/Course-Url/T-00.1000_d1/exercises/3/submissions/3/', breadcrumb[3][1])

    def test_submission_upload_dir(self):
        from exercise.submission_models import build_upload_dir
        self.assertEqual("submissions/course_instance_1/exercise_3/users_1/submission_1/test_file_name", build_upload_dir(self.submitted_file1, "test_file_name"))
        self.assertEqual("submissions/course_instance_1/exercise_3/users_1-4/submission_2/test_file_name", build_upload_dir(self.submitted_file2, "test_file_name"))

    def test_presentation_summary_empty(self):
        summary = UserCourseSummary(self.course_instance, self.user)
        self.assertEqual(summary.get_exercise_count(), 5)
        self.assertEqual(summary.get_max_points(), 400)
        self.assertEqual(summary.get_total_points(), 0)
        self.assertEqual(summary.get_completed_percentage(), 0)
        
    def test_presentation_summary(self):
        
        self.submission.set_points(10, 10)
        self.submission.save()
        summary = UserCourseSummary(self.course_instance, self.user)
        self.assertEqual(summary.get_exercise_count(), 5)
        self.assertEqual(summary.get_max_points(), 400)
        self.assertEqual(summary.get_total_points(), 100)
        self.assertEqual(summary.get_completed_percentage(), 25)
        
        msummary = summary.get_module_summary(self.course_module)
        self.assertEqual(msummary.get_exercise_count(), 3)
        self.assertEqual(msummary.get_max_points(), 200)
        self.assertEqual(msummary.get_total_points(), 100)
        self.assertEqual(msummary.get_completed_percentage(), 50)
        self.assertEqual(msummary.get_required_percentage(), 8)
        self.assertFalse(msummary.is_passed())
        
        csummary = summary.get_category_summary(self.learning_object_category)
        self.assertEqual(csummary.get_exercise_count(), 5)
        self.assertEqual(csummary.get_max_points(), 400)
        self.assertEqual(csummary.get_total_points(), 100)
        self.assertEqual(csummary.get_completed_percentage(), 25)
        self.assertEqual(csummary.get_required_percentage(), 1)
        self.assertFalse(csummary.is_passed())
