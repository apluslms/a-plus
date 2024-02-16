from datetime import timedelta

from django.test import TestCase
from django.test.client import Client
from django.utils import timezone

from course.models import (
    Course,
    CourseInstance,
    CourseModule,
    LearningObjectCategory,
    UserTag,
    UserTagging,
)
from exercise.exercise_models import BaseExercise
from exercise.models import ExerciseWithAttachment, Submission
from userprofile.models import User

from .models import DeadlineRuleDeviation, MaxSubmissionsRuleDeviation
from .viewbase import get_deviation_groups


class DeviationsTest(TestCase):
    def setUp(self):
        self.teacher = User(username="staff", is_staff=True)
        self.teacher.set_password("staffPassword")
        self.teacher.save()

        self.client = Client()

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

        # Truncate the datetime to seconds to make testing deadline deviations more convenient
        self.today = timezone.now().replace(microsecond=0)
        self.tomorrow = self.today + timedelta(days=1)
        self.two_days_from_now = self.today + timedelta(days=2)

        self.course_instance = CourseInstance.objects.create(
            instance_name="Fall 2011 day 1",
            starting_time=self.today,
            ending_time=self.tomorrow,
            course=self.course,
            url="T-00.1000_d1",
        )

        self.course_instance.enroll_student(self.user)
        self.course_instance.enroll_student(self.user_2)
        self.course_instance.add_teacher(self.teacher.userprofile)

        self.course_module = CourseModule.objects.create(
            name="test module",
            url="test-module",
            points_to_pass=15,
            course_instance=self.course_instance,
            opening_time=self.today,
            closing_time=self.tomorrow,
        )

        self.course_module_2 = CourseModule.objects.create(
            name="test module 2",
            url="test-module-2",
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
            url="test_exercise_1",
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
            url="test_exercise_2",
        )

        self.module_2_exercise_1 = BaseExercise.objects.create(
            name="module 2 test exercise 1",
            course_module=self.course_module_2,
            category=self.learning_object_category,
            max_points=50,
            points_to_pass=50,
            max_submissions=1,
            url="module_2_exercise_1",
        )

        self.module_2_exercise_2 = BaseExercise.objects.create(
            name="module 2 test exercise 2",
            course_module=self.course_module_2,
            category=self.learning_object_category,
            max_points=50,
            points_to_pass=50,
            max_submissions=1,
            url="module_2_exercise_2",
        )

        self.user_tag = UserTag.objects.create(
            course_instance=self.course_instance,
            name='tag_1',
        )

        self.user_tagging = UserTagging.objects.create(
            tag=self.user_tag,
            user=self.user.userprofile,
            course_instance=self.course_instance,
        )

        self.deadline_rule_deviation_u1_e1 = DeadlineRuleDeviation.objects.create(
            exercise=self.exercise_with_attachment,
            submitter=self.user.userprofile,
            granter=self.teacher.userprofile,
            extra_seconds=24*60*60, # One day
        )

        self.deadline_rule_deviation_u1_e2 = DeadlineRuleDeviation.objects.create(
            exercise=self.exercise_with_attachment_2,
            submitter=self.user.userprofile,
            granter=self.teacher.userprofile,
            extra_seconds=2*24*60*60, # Two days
        )

        self.deadline_rule_deviation_u2_e1 = DeadlineRuleDeviation.objects.create(
            exercise=self.exercise_with_attachment,
            submitter=self.user_2.userprofile,
            granter=self.teacher.userprofile,
            extra_seconds=3*24*60*60, # Three days
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
        self.assertEqual(deviation.extra_seconds, 24*60*60)

        deviation = DeadlineRuleDeviation.objects.get_max_deviation(
            self.user_2.userprofile,
            self.exercise_with_attachment,
        )
        self.assertIsNotNone(deviation)
        self.assertEqual(deviation.exercise.id, self.exercise_with_attachment.id)
        self.assertEqual(deviation.extra_seconds, 3*24*60*60)

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
                self.assertEqual(deviation.extra_seconds, 24*60*60)
            elif deviation.exercise.id == self.exercise_with_attachment_2.id:
                self.assertEqual(deviation.extra_seconds, 2*24*60*60)
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
                self.assertEqual(deviation.extra_seconds, 3*24*60*60)
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
        self.assertEqual(deviation.extra_seconds, 3*24*60*60)

        deviation = DeadlineRuleDeviation.objects.get_max_deviation(
            self.user_2.userprofile,
            self.exercise_with_attachment,
        )
        self.assertIsNotNone(deviation)
        self.assertEqual(deviation.exercise.id, self.exercise_with_attachment.id)
        self.assertEqual(deviation.extra_seconds, 3*24*60*60)

    def test_update_by_form(self):
        deviation = DeadlineRuleDeviation(
            exercise=self.exercise_with_attachment,
            submitter=self.user.userprofile,
        )
        deviation.update_by_form({
            'seconds': 60*60,
            'without_late_penalty': False,
        })
        self.assertEqual(deviation.extra_seconds, 60*60)
        self.assertEqual(deviation.without_late_penalty, False)

        deviation.update_by_form({
            'new_date': timezone.make_naive(self.two_days_from_now),
            'without_late_penalty': True,
        })
        self.assertEqual(deviation.extra_seconds, 24*60*60)
        self.assertEqual(deviation.without_late_penalty, True)
        deviation = MaxSubmissionsRuleDeviation(
            exercise=self.exercise_with_attachment,
            submitter=self.user.userprofile,
        )

        deviation.update_by_form({
            'extra_submissions': 5,
        })
        self.assertEqual(deviation.extra_submissions, 5)

    def test_is_groupable(self):
        deviation_1 = DeadlineRuleDeviation(
            exercise=self.exercise_with_attachment,
            submitter=self.user.userprofile,
            extra_seconds=60*60,
            without_late_penalty=False,
        )
        deviation_2 = DeadlineRuleDeviation(
            exercise=self.exercise_with_attachment_2,
            submitter=self.user_2.userprofile,
            extra_seconds=60*60,
            without_late_penalty=False,
        )
        self.assertTrue(deviation_1.is_groupable(deviation_2))

        deviation_2.extra_seconds = 120*60
        self.assertFalse(deviation_1.is_groupable(deviation_2))

        deviation_2.extra_seconds = 60*60
        deviation_2.without_late_penalty = True
        self.assertFalse(deviation_1.is_groupable(deviation_2))

        deviation_1 = MaxSubmissionsRuleDeviation(
            exercise=self.exercise_with_attachment,
            submitter=self.user.userprofile,
            extra_submissions=5,
        )
        deviation_2 = MaxSubmissionsRuleDeviation(
            exercise=self.exercise_with_attachment_2,
            submitter=self.user_2.userprofile,
            extra_submissions=5,
        )
        self.assertTrue(deviation_1.is_groupable(deviation_2))

        deviation_2.extra_submissions = 10
        self.assertFalse(deviation_1.is_groupable(deviation_2))

    def test_get_deviation_groups(self):
        # The deviations of user 1 can't be grouped because of different extra seconds
        # The deviations of user 2 can't be grouped because there is only one deviation
        groups = list(get_deviation_groups(DeadlineRuleDeviation.objects.all()))
        deviations, can_group, group_id, _ = groups[0]
        self.assertEqual(len(deviations), 2)
        self.assertFalse(can_group)
        self.assertIsNone(group_id)
        deviations, can_group, group_id, _ = groups[1]
        self.assertEqual(len(deviations), 1)
        self.assertFalse(can_group)
        self.assertIsNone(group_id)

        self.deadline_rule_deviation_u1_e1.extra_seconds = 60*60
        self.deadline_rule_deviation_u1_e1.save()
        self.deadline_rule_deviation_u1_e2.extra_seconds = 60*60
        self.deadline_rule_deviation_u1_e2.save()
        self.deadline_rule_deviation_u2_e1.extra_seconds = 60*60
        self.deadline_rule_deviation_u2_e1.save()

        # The deviations of user 1 can now be grouped
        groups = list(get_deviation_groups(DeadlineRuleDeviation.objects.all()))
        deviations, can_group, group_id, _ = groups[0]
        self.assertEqual(len(deviations), 2)
        self.assertTrue(can_group)
        self.assertEqual(group_id, f'{self.user.id}.{self.course_module.id}')

        extra_exercise = BaseExercise.objects.create(
            name="extra exercise",
            course_module=self.course_module,
            category=self.learning_object_category,
            max_points=50,
            points_to_pass=50,
            max_submissions=1,
        )

        # The deviations of user 1 can no longer be grouped because there is an exercise without a deviation
        groups = list(get_deviation_groups(DeadlineRuleDeviation.objects.all()))
        deviations, can_group, group_id, _ = groups[0]
        self.assertEqual(len(deviations), 2)
        self.assertFalse(can_group)
        self.assertIsNone(group_id)

        # Reset original values
        self.deadline_rule_deviation_u1_e1.extra_seconds = 24*60*60
        self.deadline_rule_deviation_u1_e1.save()
        self.deadline_rule_deviation_u1_e2.extra_seconds = 2*24*60*60
        self.deadline_rule_deviation_u1_e2.save()
        self.deadline_rule_deviation_u2_e1.extra_seconds = 3*24*60*60
        self.deadline_rule_deviation_u2_e1.save()
        extra_exercise.delete()

    def test_add_deadline_deviations(self):
        self.client.login(username="staff", password="staffPassword")
        add_deadline_deviations_url = self.course_instance.get_url("deviations-add-dl")

        # Module and user tag provided
        response = self.client.post(
            add_deadline_deviations_url,
            {
                'module': [self.course_module_2.id],
                'submitter_tag': [self.user_tag.id],
                'seconds': 60*60,
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, add_deadline_deviations_url)

        deviation = DeadlineRuleDeviation.objects.get(
            exercise=self.module_2_exercise_1,
            submitter=self.user.userprofile,
        )
        self.assertEqual(deviation.extra_seconds, 60*60)
        deviation.delete()
        deviation = DeadlineRuleDeviation.objects.get(
            exercise=self.module_2_exercise_2,
            submitter=self.user.userprofile,
        )
        self.assertEqual(deviation.extra_seconds, 60*60)
        deviation.delete()

        with self.assertRaises(DeadlineRuleDeviation.DoesNotExist):
            DeadlineRuleDeviation.objects.get(
                exercise=self.module_2_exercise_1,
                submitter=self.user_2.userprofile,
            )
        with self.assertRaises(DeadlineRuleDeviation.DoesNotExist):
            DeadlineRuleDeviation.objects.get(
                exercise=self.module_2_exercise_2,
                submitter=self.user_2.userprofile,
            )

        # Exercise and submitters provided
        response = self.client.post(
            add_deadline_deviations_url,
            {
                'exercise': [self.module_2_exercise_1.id],
                'submitter': [self.user.userprofile.id, self.user_2.userprofile.id],
                'seconds': 120*60,
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, add_deadline_deviations_url)

        deviation = DeadlineRuleDeviation.objects.get(
            exercise=self.module_2_exercise_1,
            submitter=self.user.userprofile,
        )
        self.assertEqual(deviation.extra_seconds, 120*60)
        deviation.delete()
        deviation = DeadlineRuleDeviation.objects.get(
            exercise=self.module_2_exercise_1,
            submitter=self.user_2.userprofile,
        )
        self.assertEqual(deviation.extra_seconds, 120*60)
        deviation.delete()

        with self.assertRaises(DeadlineRuleDeviation.DoesNotExist):
            DeadlineRuleDeviation.objects.get(
                exercise=self.module_2_exercise_2,
                submitter=self.user.userprofile,
            )
        with self.assertRaises(DeadlineRuleDeviation.DoesNotExist):
            DeadlineRuleDeviation.objects.get(
                exercise=self.module_2_exercise_2,
                submitter=self.user_2.userprofile,
            )

        # All fields provided
        response = self.client.post(
            add_deadline_deviations_url,
            {
                'module': [self.course_module_2.id],
                'exercise': [self.module_2_exercise_1.id],
                'submitter_tag': [self.user_tag.id],
                'submitter': [self.user_2.userprofile.id],
                'seconds': 180*60,
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, add_deadline_deviations_url)

        deviation = DeadlineRuleDeviation.objects.get(
            exercise=self.module_2_exercise_1,
            submitter=self.user.userprofile,
        )
        self.assertEqual(deviation.extra_seconds, 180*60)
        deviation.delete()
        deviation = DeadlineRuleDeviation.objects.get(
            exercise=self.module_2_exercise_1,
            submitter=self.user_2.userprofile,
        )
        self.assertEqual(deviation.extra_seconds, 180*60)
        deviation.delete()
        deviation = DeadlineRuleDeviation.objects.get(
            exercise=self.module_2_exercise_2,
            submitter=self.user.userprofile,
        )
        self.assertEqual(deviation.extra_seconds, 180*60)
        deviation.delete()
        deviation = DeadlineRuleDeviation.objects.get(
            exercise=self.module_2_exercise_2,
            submitter=self.user_2.userprofile,
        )
        self.assertEqual(deviation.extra_seconds, 180*60)
        deviation.delete()

        # No extra deviations should have been created
        self.assertEqual(DeadlineRuleDeviation.objects.filter(
            exercise__course_module=self.course_module_2
        ).count(), 0)

    def test_override_deadline_deviations(self):
        self.client.login(username="staff", password="staffPassword")
        add_deadline_deviations_url = self.course_instance.get_url("deviations-add-dl")
        override_deadline_deviations_url = self.course_instance.get_url("deviations-override-dl")

        # Create initial deviation
        response = self.client.post(
            add_deadline_deviations_url,
            {
                'exercise': [self.module_2_exercise_1.id],
                'submitter': [self.user.userprofile.id],
                'seconds': 30*60,
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, add_deadline_deviations_url)

        self.assertEqual(
            DeadlineRuleDeviation.objects.get(
                exercise=self.module_2_exercise_1,
                submitter=self.user.userprofile,
            ).extra_seconds,
            30*60,
        )

        # Create new deviations, one overlapping the initial deviation
        response = self.client.post(
            add_deadline_deviations_url,
            {
                'exercise': [self.module_2_exercise_1.id, self.module_2_exercise_2.id],
                'submitter': [self.user.userprofile.id],
                'seconds': 60*60,
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, override_deadline_deviations_url)

        self.assertEqual(
            DeadlineRuleDeviation.objects.get(
                exercise=self.module_2_exercise_1,
                submitter=self.user.userprofile,
            ).extra_seconds,
            30*60,
        )
        with self.assertRaises(DeadlineRuleDeviation.DoesNotExist):
            DeadlineRuleDeviation.objects.get(
                exercise=self.module_2_exercise_2,
                submitter=self.user.userprofile,
            )

        # Override the overlapping deviation
        response = self.client.post(
            override_deadline_deviations_url,
            {
                'override': [f'{self.user.userprofile.id}.{self.module_2_exercise_1.id}'],
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, add_deadline_deviations_url)

        self.assertEqual(
            DeadlineRuleDeviation.objects.get(
                exercise=self.module_2_exercise_1,
                submitter=self.user.userprofile,
            ).extra_seconds,
            60*60,
        )
        self.assertEqual(
            DeadlineRuleDeviation.objects.get(
                exercise=self.module_2_exercise_2,
                submitter=self.user.userprofile,
            ).extra_seconds,
            60*60,
        )

        # Create deviations overlapping both deviations, override 2nd one
        response = self.client.post(
            add_deadline_deviations_url,
            {
                'exercise': [self.module_2_exercise_1.id, self.module_2_exercise_2.id],
                'submitter': [self.user.userprofile.id],
                'seconds': 120*60,
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, override_deadline_deviations_url)

        response = self.client.post(
            override_deadline_deviations_url,
            {
                'override': [f'{self.user.userprofile.id}.{self.module_2_exercise_2.id}'],
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, add_deadline_deviations_url)

        self.assertEqual(
            DeadlineRuleDeviation.objects.get(
                exercise=self.module_2_exercise_1,
                submitter=self.user.userprofile,
            ).extra_seconds,
            60*60,
        )
        self.assertEqual(
            DeadlineRuleDeviation.objects.get(
                exercise=self.module_2_exercise_2,
                submitter=self.user.userprofile,
            ).extra_seconds,
            120*60,
        )

        DeadlineRuleDeviation.objects.filter(exercise__course_module=self.course_module_2).delete()

    def test_remove_deadline_deviations(self):
        self.client.login(username="staff", password="staffPassword")
        add_deadline_deviations_url = self.course_instance.get_url("deviations-add-dl")
        remove_deadline_deviations_url = self.course_instance.get_url("deviations-remove-dl")

        # Create initial deviations
        response = self.client.post(
            add_deadline_deviations_url,
            {
                'exercise': [self.module_2_exercise_1.id, self.module_2_exercise_2.id],
                'submitter': [self.user.userprofile.id],
                'seconds': 45*60,
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, add_deadline_deviations_url)

        self.assertEqual(
            DeadlineRuleDeviation.objects.get(
                exercise=self.module_2_exercise_1,
                submitter=self.user.userprofile,
            ).extra_seconds,
            45*60,
        )
        self.assertEqual(
            DeadlineRuleDeviation.objects.get(
                exercise=self.module_2_exercise_2,
                submitter=self.user.userprofile,
            ).extra_seconds,
            45*60,
        )

        # Remove one deviation
        response = self.client.post(
            remove_deadline_deviations_url,
            {
                'exercise': [self.module_2_exercise_1.id],
                'submitter': [self.user.userprofile.id],
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, remove_deadline_deviations_url)

        with self.assertRaises(DeadlineRuleDeviation.DoesNotExist):
            DeadlineRuleDeviation.objects.get(
                exercise=self.module_2_exercise_1,
                submitter=self.user.userprofile,
            )

        # Remove the other deviation using module and user tag
        response = self.client.post(
            remove_deadline_deviations_url,
            {
                'module': [self.course_module_2.id],
                'submitter_tag': [self.user_tag.id],
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, remove_deadline_deviations_url)

        with self.assertRaises(DeadlineRuleDeviation.DoesNotExist):
            DeadlineRuleDeviation.objects.get(
                exercise=self.module_2_exercise_2,
                submitter=self.user.userprofile,
            )
