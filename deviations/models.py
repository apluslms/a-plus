from datetime import timedelta

from django.urls import reverse
from django.db import models

from exercise.exercise_models import BaseExercise
from userprofile.models import UserProfile
from lib.models import UrlMixin


class SubmissionRuleDeviation(UrlMixin, models.Model):
    """
    An abstract model binding a user to an exercise stating that there is some
    kind of deviation from the normal submission boundaries, that is, special
    treatment related to the submissions of that particular user to that
    particular exercise.

    If there are many submitters submitting an exercise out of bounds of the
    default bounds, all of the submitters must have an allowing instance of
    SubmissionRuleDeviation subclass in order for the submission to be allowed.
    """
    exercise = models.ForeignKey(BaseExercise, on_delete=models.CASCADE)
    submitter = models.ForeignKey(UserProfile, on_delete=models.CASCADE)

    class Meta:
        abstract = True
        unique_together = ["exercise", "submitter"]

    def get_url_kwargs(self):
        return dict(deviation_id=self.id, **self.exercise.course_instance.get_url_kwargs())


class DeadlineRuleDeviation(SubmissionRuleDeviation):
    extra_minutes = models.IntegerField()
    without_late_penalty = models.BooleanField(default=True)

    class Meta(SubmissionRuleDeviation.Meta):
        pass

    def get_extra_time(self):
        return timedelta(minutes=self.extra_minutes)

    def get_new_deadline(self):
        return self.get_normal_deadline() + self.get_extra_time()

    def get_normal_deadline(self):
        return self.exercise.course_module.closing_time


class MaxSubmissionsRuleDeviation(SubmissionRuleDeviation):
    extra_submissions = models.IntegerField()

    class Meta(SubmissionRuleDeviation.Meta):
        pass
