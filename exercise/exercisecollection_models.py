from django.contrib.auth.models import User # pylint: disable=imported-auth-user
from django.utils import timezone
from django.db import models
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.utils.translation import gettext_lazy as _

from django.core.exceptions import ValidationError

from exercise.exercise_summary import UserExerciseSummary
from .exercise_models import BaseExercise
from .submission_models import Submission
from course.models import LearningObjectCategory




class ExerciseCollection(BaseExercise):
    # Submissions must persist even if the target course or category
    #  gets destroyed.
    target_category = models.ForeignKey(
        LearningObjectCategory,
        verbose_name=_('LABEL_TARGET_CATEGORY'),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _('MODEL_NAME_EXERCISE_COLLECTION')
        verbose_name_plural = _('MODEL_NAME_EXERCISE_COLLECTION_PLURAL')


    # Clearing possible sources for erronous functionality
    def clean(self):
        super().clean()
        errors = {}
        if self.target_category.id == self.category.id:
            errors['target_category'] = 'Cannot set own category as target category.'

        if self.max_submissions != 1:
            errors['max_submissions'] = 'Exercise Collection can have only 1 submission.'
        if self.max_group_size != 1:
            errors['max_group_size'] = 'Exercise Collection can have only 1 submitter'
        if self.min_group_size != 1:
            errors['min_group_size'] = 'Exercise Collection can have only 1 submitter'

        if errors:
            raise ValidationError(errors)

    # Allows viewing of submissions
    # Not actually user submittable
    @property
    def is_submittable(self):
        return True


    # Calculates the sum of best submissions in target category
    #
    # returns None:
    #  * Timing doesn't allow submissions
    #  * Target category doesn't have exercises with points
    #
    def get_points(self, user, no_scaling=False):
        total_points = 0
        tc_max_points = self.target_category_maxpoints
        max_points = self.max_points

        if tc_max_points == 0:
            return None


        timing, _d1 = self.get_timing([user.userprofile],timezone.now())

        if (
            timing == self.TIMING.CLOSED_AFTER or # pylint: disable=consider-using-in
            timing == self.TIMING.ARCHIVED or
            timing == self.TIMING.CLOSED_BEFORE or
            timing == self.TIMING.UNOFFICIAL
        ):
            return None

        for exercise in self.exercises:
            summary = UserExerciseSummary(exercise, user)
            if summary.best_submission is not None:
                total_points += summary.best_submission.grade


        if timing == self.TIMING.LATE:
            total_points = round(total_points * (1 - self.course_module.late_submission_penalty))

        if tc_max_points == max_points or no_scaling:
            return total_points

        total_points = total_points / (tc_max_points / max_points)

        return total_points


    # Used when staff forces regrading
    def grade(self, submission, request=None): # pylint: disable=arguments-differ
        user = list(submission.submitters.all())[0]
        self.check_submission(user, forced=True)


    # Updates submission for ExerciseCollection
    # Updated submission is saved only if grade has changed
    # Parameters:
    #   * no_update: Doesn't update grade if submission exists
    #   * forced: Updates submission even if grade hasn't changed
    #
    def check_submission(self, user, no_update=False, forced=False):

        if no_update and self.is_submitted(user) and not forced:
            return

        # Create new submission or use previous
        if not self.is_submitted(user):
            current_submission = Submission.objects.create(
            exercise=self,
            feedback="",
            grade=-1,
            )
            current_submission.clean()
            current_submission.save()
        else:
            submissions = self.get_submissions_for_student(user.userprofile)
            current_submission = submissions[0]


        new_grade = self.get_points(user)

        if new_grade == current_submission.grade and not forced:
            return


        grading_data, feedback = self._generate_grading_data(user.userprofile)


        current_submission.grade = new_grade
        current_submission.submission_time = timezone.now()
        current_submission.status = Submission.STATUS.READY
        current_submission.submitters.set([user.userprofile])
        current_submission.grading_data = grading_data
        current_submission.feedback = feedback
        current_submission.clean()
        current_submission.save()



    # Check if user has a submission for this exercise
    def is_submitted(self, user: User) -> bool:
        return self.get_submissions_for_student(user.userprofile).exists()


    # Property to access max_points in target category
    @property
    def target_category_maxpoints(self):
        max_points = 0

        for exercise in self.exercises:
            max_points += exercise.max_points

        return max_points


    # Property to access exercises in target category
    @property
    def exercises(self):
        return BaseExercise.objects.filter(
            category=self.target_category
        ).order_by('id')

    # There are always submissions left from system's point of view
    def one_has_submissions(self, students):
        return True

    # Generates feedback and grading_data
    # Feedback is in HTML format
    # grading_data is currently blank
    def _generate_grading_data(self, profile):
        feedback = ""
        grading_data = ""

        exercise_counter = 1
        for exercise in self.exercises:

            submission = UserExerciseSummary(exercise, profile.user).best_submission
            if submission is None:
                grade = 0
            else:
                grade = submission.grade

            feedback += "Exercise {}: {}/{}\n  Course: {} - {}\n  Exercise: {}\n".format(
                exercise_counter,
                grade,
                exercise.max_points,
                exercise.category.course_instance.course.name,
                exercise.category.course_instance.instance_name,
                exercise.name,
            )
            exercise_counter += 1

        feedback = "<pre>\n" + feedback + "\n</pre>\n"
        return {"grading_data": grading_data}, feedback



# Updates submissions if new submission is in any ExerciseCollection's target category.
# ! Probably needs Cache-optimization
@receiver(post_save, sender=Submission)
def update_exercise_collection_submission(sender, instance, **kwargs): # pylint: disable=unused-argument
    collections = ExerciseCollection.objects.filter(target_category=instance.exercise.category)
    if not collections:
        return

    profile = instance.submitters.first()
    if not profile:
        return

    for collection in collections:
        collection.check_submission(profile.user)
