from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from course.models import Course, CourseInstance, CourseModule, \
    LearningObjectCategory
from deviations.models import DeadlineRuleDeviation
from exercise.models import ExerciseWithAttachment, Submission
from userprofile.models import User


class DeviationsTest(TestCase):
    def setUp(self):
        self.user = User(username="testUser", first_name="First", last_name="Last")
        self.user.set_password("testPassword")
        self.user.save()

        self.user_2 = User(username="testUser2", first_name="First2", last_name="Last2")
        self.user_2.set_password("testPassword2")
        self.user_2.save()

        self.course = Course.objects.create(
            name="test course",
            code="123456",
            url="Course-Url",
        )

        self.today = timezone.now()
        self.tomorrow = self.today + timedelta(days=1)
        self.two_days_from_now = self.today + timedelta(days=2)

        self.course_instance = CourseInstance.objects.create(
            instance_name="Fall 2011 day 1",
            starting_time=self.today,
            ending_time=self.tomorrow,
            course=self.course,
            url="T-00.1000_d1",
        )

        self.course_module = CourseModule.objects.create(
            name="test module",
            url="test-module",
            points_to_pass=15,
            course_instance=self.course_instance,
            opening_time=self.today,
            closing_time=self.tomorrow,
        )

        self.learning_object_category = LearningObjectCategory.objects.create(
            name="test category",
            course_instance=self.course_instance,
            points_to_pass=5,
        )

        self.exercise_with_attachment = ExerciseWithAttachment.objects.create(
            name="test exercise 3",
            course_module=self.course_module,
            category=self.learning_object_category,
            max_points=50,
            points_to_pass=50,
            max_submissions=1,
            files_to_submit="test1.txt|test2.txt|img.png",
            content="test_instructions",
        )

        self.exercise_with_attachment_2 = ExerciseWithAttachment.objects.create(
            name="test exercise 4",
            course_module=self.course_module,
            category=self.learning_object_category,
            max_points=50,
            points_to_pass=50,
            max_submissions=1,
            files_to_submit="test1.txt|test2.txt|img.png",
            content="test_instructions",
        )

        self.deadline_rule_deviation_u1_e1 = DeadlineRuleDeviation.objects.create(
            exercise=self.exercise_with_attachment,
            submitter=self.user.userprofile,
            extra_minutes=1440, # One day
        )

        self.deadline_rule_deviation_u1_e2 = DeadlineRuleDeviation.objects.create(
            exercise=self.exercise_with_attachment_2,
            submitter=self.user.userprofile,
            extra_minutes=2880, # Two days
        )

        self.deadline_rule_deviation_u2_e1 = DeadlineRuleDeviation.objects.create(
            exercise=self.exercise_with_attachment,
            submitter=self.user_2.userprofile,
            extra_minutes=4320, # Three days
        )

    def test_deadline_rule_deviation_extra_time(self):
        self.assertEqual(timedelta(days=1), self.deadline_rule_deviation_u1_e1.get_extra_time())

    def test_deadline_rule_deviation_new_deadline(self):
        self.assertEqual(self.two_days_from_now, self.deadline_rule_deviation_u1_e1.get_new_deadline())

    def test_deadline_rule_deviation_new_deadline_with_normal_deadline(self):
        self.assertEqual(self.tomorrow, self.deadline_rule_deviation_u1_e1.get_new_deadline(self.today))

    def test_deadline_rule_deviation_normal_deadline(self):
        self.assertEqual(self.tomorrow, self.deadline_rule_deviation_u1_e1.get_normal_deadline())

    def test_get_max_deviations(self):
        # Test that the get_max_deviations method returns the correct deviation
        # when one exercise is passed into the method.

        deviation = DeadlineRuleDeviation.objects.get_max_deviation(
            self.user.userprofile,
            self.exercise_with_attachment,
        )
        self.assertIsNotNone(deviation)
        self.assertEqual(deviation.exercise.id, self.exercise_with_attachment.id)
        self.assertEqual(deviation.extra_minutes, 1440)

        deviation = DeadlineRuleDeviation.objects.get_max_deviation(
            self.user_2.userprofile,
            self.exercise_with_attachment,
        )
        self.assertIsNotNone(deviation)
        self.assertEqual(deviation.exercise.id, self.exercise_with_attachment.id)
        self.assertEqual(deviation.extra_minutes, 4320)

    def test_get_max_deviations_multiple(self):
        # Test that the get_max_deviations method returns the correct deviation
        # when multiple exercises are passed into the method.

        deviations = DeadlineRuleDeviation.objects.get_max_deviations(
            self.user.userprofile,
            [self.exercise_with_attachment, self.exercise_with_attachment_2],
        )
        counter = 0
        for deviation in deviations:
            counter += 1
            if deviation.exercise.id == self.exercise_with_attachment.id:
                self.assertEqual(deviation.extra_minutes, 1440)
            elif deviation.exercise.id == self.exercise_with_attachment_2.id:
                self.assertEqual(deviation.extra_minutes, 2880)
            else:
                raise self.failureException('Unexpected exercise returned')
        self.assertEqual(counter, 2)

        deviations = DeadlineRuleDeviation.objects.get_max_deviations(
            self.user_2.userprofile,
            [self.exercise_with_attachment, self.exercise_with_attachment_2],
        )
        counter = 0
        for deviation in deviations:
            counter += 1
            if deviation.exercise.id == self.exercise_with_attachment.id:
                self.assertEqual(deviation.extra_minutes, 4320)
            else:
                raise self.failureException('Unexpected exercise returned')
        self.assertEqual(counter, 1)

    def test_get_max_deviations_group(self):
        # Test that the get_max_deviations method returns the correct deviation
        # when there is a group submission with both users. In this case,
        # user 2's deviation should also be returned for user 1.

        submission = Submission.objects.create(
            exercise=self.exercise_with_attachment,
            status=Submission.STATUS.READY,
        )
        submission.submitters.add(self.user.userprofile, self.user_2.userprofile)

        deviation = DeadlineRuleDeviation.objects.get_max_deviation(
            self.user.userprofile,
            self.exercise_with_attachment,
        )
        self.assertIsNotNone(deviation)
        self.assertEqual(deviation.exercise.id, self.exercise_with_attachment.id)
        self.assertEqual(deviation.extra_minutes, 4320)

        deviation = DeadlineRuleDeviation.objects.get_max_deviation(
            self.user_2.userprofile,
            self.exercise_with_attachment,
        )
        self.assertIsNotNone(deviation)
        self.assertEqual(deviation.exercise.id, self.exercise_with_attachment.id)
        self.assertEqual(deviation.extra_minutes, 4320)
