from datetime import timedelta

from django.urls import reverse
from django.db import models
from django.utils.translation import gettext_lazy as _

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
    exercise = models.ForeignKey(BaseExercise,
        verbose_name=_('LABEL_EXERCISE'),
        on_delete=models.CASCADE,
    )
    submitter = models.ForeignKey(UserProfile,
        verbose_name=_('LABEL_SUBMITTER'),
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = _('MODEL_NAME_SUBMISSION_RULE_DEVIATION')
        verbose_name_plural = _('MODEL_NAME_SUBMISSION_RULE_DEVIATION_PLURAL')
        abstract = True
        unique_together = ["exercise", "submitter"]

    def get_url_kwargs(self):
        return dict(deviation_id=self.id, **self.exercise.course_instance.get_url_kwargs())


class DeadlineRuleDeviation(SubmissionRuleDeviation):
    extra_minutes = models.IntegerField(
        verbose_name=_('LABEL_EXTRA_MINUTES'),
    )
    without_late_penalty = models.BooleanField(
        verbose_name=_('LABEL_WITHOUT_LATE_PENALTY'),
        default=True,
    )

    class Meta(SubmissionRuleDeviation.Meta):
        verbose_name = _('MODEL_NAME_DEADLINE_RULE_DEVIATION')
        verbose_name_plural = _('MODEL_NAME_DEADLINE_RULE_DEVIATION_PLURAL')

    def get_extra_time(self):
        return timedelta(minutes=self.extra_minutes)

    def get_new_deadline(self):
        return self.get_normal_deadline() + self.get_extra_time()

    def get_normal_deadline(self):
        return self.exercise.course_module.closing_time


class MaxSubmissionsRuleDeviation(SubmissionRuleDeviation):
    extra_submissions = models.IntegerField(
        verbose_name=_('LABEL_EXTRA_SUBMISSIONS'),
    )

    class Meta(SubmissionRuleDeviation.Meta):
        verbose_name = _('MODEL_NAME_MAX_SUBMISSIONS_RULE_DEVIATION')
        verbose_name_plural = _('MODEL_NAME_MAX_SUBMISSIONS_RULE_DEVIATION_PLURAL')
