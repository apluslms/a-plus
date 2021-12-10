from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Generic, Iterable, Optional, TypeVar, Union

from django.urls import reverse
from django.db import models
from django.utils.translation import gettext_lazy as _

from exercise.exercise_models import BaseExercise
from exercise.submission_models import Submission
from userprofile.models import UserProfile
from lib.models import UrlMixin


TModel = TypeVar('TModel', bound='SubmissionRuleDeviation')
class SubmissionRuleDeviationManager(models.Manager[TModel], Generic[TModel]):
    max_order_by: str

    def get_max_deviations(
        self,
        submitter: UserProfile,
        exercises: Iterable[Union[BaseExercise, int]],
    ) -> Iterable[TModel]:
        """
        Returns the maximum deviations for the given submitter in the given
        exercises (one deviation per exercise is returned). The deviation may
        be granted to the submitter directly, or to some other submitter in
        their group.
        """
        deviations = (
            self.filter(
                models.Q(exercise__in=exercises)
                & (
                    # Check that the owner of the deviation is the user, or
                    # some other user who has submitted the deviation's
                    # exercise with the user.
                    models.Q(submitter=submitter)
                    | models.Exists(
                        # Note the two 'submitters' filters.
                        Submission.objects.filter(
                            exercise=models.OuterRef('exercise'),
                            submitters=models.OuterRef('submitter'),
                        ).filter(
                            submitters=submitter,
                        )
                    )
                )
            )
            .select_related('exercise')
            .order_by('exercise', self.max_order_by)
        )

        previous_exercise_id = None
        for deviation in deviations:
            if deviation.exercise.id == previous_exercise_id:
                continue
            previous_exercise_id = deviation.exercise.id
            yield deviation

    def get_max_deviation(self, submitter: UserProfile, exercise: Union[BaseExercise, int]) -> Optional[TModel]:
        """
        Returns the maximum deviation for the given submitter in the given
        exercise. The deviation may be granted to the submitter directly, or to
        some other submitter in their group.
        """
        deviations = self.get_max_deviations(submitter, [exercise])
        for deviation in deviations:
            return deviation


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
    granter = models.ForeignKey(UserProfile,
        verbose_name=_('LABEL_GRANTER'),
        on_delete=models.SET_NULL,
        related_name='+',
        blank=True,
        null=True,
    )
    grant_time = models.DateTimeField(
        verbose_name=_('LABEL_GRANT_TIME'),
        auto_now=True,
        blank=True,
        null=True,
    )

    if TYPE_CHECKING:
        id: models.AutoField

    class Meta:
        verbose_name = _('MODEL_NAME_SUBMISSION_RULE_DEVIATION')
        verbose_name_plural = _('MODEL_NAME_SUBMISSION_RULE_DEVIATION_PLURAL')
        abstract = True
        unique_together = ["exercise", "submitter"]

    def get_url_kwargs(self):
        return dict(deviation_id=self.id, **self.exercise.course_instance.get_url_kwargs())


class DeadlineRuleDeviationManager(SubmissionRuleDeviationManager['DeadlineRuleDeviation']):
    max_order_by = "-extra_minutes"


class DeadlineRuleDeviation(SubmissionRuleDeviation):
    extra_minutes = models.IntegerField(
        verbose_name=_('LABEL_EXTRA_MINUTES'),
    )
    without_late_penalty = models.BooleanField(
        verbose_name=_('LABEL_WITHOUT_LATE_PENALTY'),
        default=True,
    )

    objects = DeadlineRuleDeviationManager()

    class Meta(SubmissionRuleDeviation.Meta):
        verbose_name = _('MODEL_NAME_DEADLINE_RULE_DEVIATION')
        verbose_name_plural = _('MODEL_NAME_DEADLINE_RULE_DEVIATION_PLURAL')

    def get_extra_time(self):
        return timedelta(minutes=self.extra_minutes)

    def get_new_deadline(self, normal_deadline: Optional[datetime] = None) -> datetime:
        """
        Returns the new deadline after adding the extra time to the normal
        deadline.

        The `normal_deadline` argument can be provided if it is known by the
        caller, to avoid querying it.
        """
        if normal_deadline is None:
            normal_deadline = self.get_normal_deadline()
        return normal_deadline + self.get_extra_time()

    def get_normal_deadline(self):
        return self.exercise.course_module.closing_time


class MaxSubmissionsRuleDeviationManager(SubmissionRuleDeviationManager['MaxSubmissionsRuleDeviation']):
    max_order_by = "-extra_submissions"


class MaxSubmissionsRuleDeviation(SubmissionRuleDeviation):
    extra_submissions = models.IntegerField(
        verbose_name=_('LABEL_EXTRA_SUBMISSIONS'),
    )

    objects = MaxSubmissionsRuleDeviationManager()

    class Meta(SubmissionRuleDeviation.Meta):
        verbose_name = _('MODEL_NAME_MAX_SUBMISSIONS_RULE_DEVIATION')
        verbose_name_plural = _('MODEL_NAME_MAX_SUBMISSIONS_RULE_DEVIATION_PLURAL')
