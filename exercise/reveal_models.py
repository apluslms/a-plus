import datetime
from typing import Optional, TYPE_CHECKING

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from .reveal_states import BaseRevealState


class RevealRule(models.Model):
    """
    Determines whether some information (e.g. submission feedback, model
    solutions) can be revealed to students.
    """

    class TRIGGER(models.IntegerChoices):
        MANUAL = 1, _('TRIGGER_MANUAL')
        IMMEDIATE = 2, _('TRIGGER_IMMEDIATE')
        TIME = 3, _('TRIGGER_TIME')
        DEADLINE = 4, _('TRIGGER_DEADLINE')
        DEADLINE_ALL = 5, _('TRIGGER_DEADLINE_ALL')
        COMPLETION = 6, _('TRIGGER_COMPLETION')
        DEADLINE_OR_FULL_POINTS = 7, _('TRIGGER_DEADLINE_OR_FULL_POINTS')

    trigger = models.IntegerField(choices=TRIGGER.choices,
        verbose_name=_('LABEL_TRIGGER'))
    delay_minutes = models.IntegerField(blank=True, null=True,
        verbose_name=_('LABEL_DELAY_MINUTES'))
    time = models.DateTimeField(blank=True, null=True,
        verbose_name=_('LABEL_TIME'))
    currently_revealed = models.BooleanField(default=False,
        verbose_name=_('LABEL_CURRENTLY_REVEALED'))
    show_zero_points_immediately = models.BooleanField(default=False,
        verbose_name=_('LABEL_SHOW_ZERO_POINTS_IMMEDIATELY'))

    class Meta:
        verbose_name = _('MODEL_NAME_REVEAL_RULE')
        verbose_name_plural = _('MODEL_NAME_REVEAL_RULE_PLURAL')

    def is_revealed(self, state: 'BaseRevealState', time: Optional[datetime.datetime] = None) -> bool:
        """
        Returns True if, based on the provided state, the information should
        be revealed to the student.

        If a time is provided, visibility is checked for that specific time.
        Otherwise, the current time is used.
        """
        if self.trigger == RevealRule.TRIGGER.MANUAL:
            return self.currently_revealed
        if self.trigger == RevealRule.TRIGGER.IMMEDIATE:
            return True
        if self.trigger in [
            RevealRule.TRIGGER.TIME,
            RevealRule.TRIGGER.DEADLINE,
            RevealRule.TRIGGER.DEADLINE_ALL,
        ]:
            return self._is_revealed_due_to_time(state, time)
        if self.trigger == RevealRule.TRIGGER.COMPLETION:
            return self._is_revealed_due_to_full_points(state) or self._is_revealed_due_to_max_submissions(state)
        if self.trigger == RevealRule.TRIGGER.DEADLINE_OR_FULL_POINTS:
            return self._is_revealed_due_to_full_points(state) or self._is_revealed_due_to_time(state, time)

        return False

    def get_reveal_time(self, state: 'BaseRevealState') -> Optional[datetime.datetime]:
        """
        Returns the time at which `is_reveal` will be true, or `None` if the
        time is indeterminate (depends on actions such as the student
        completing the exercise).
        """

        if self.trigger == RevealRule.TRIGGER.TIME:
            return self.time
        if self.trigger in [RevealRule.TRIGGER.DEADLINE, RevealRule.TRIGGER.DEADLINE_OR_FULL_POINTS]:
            deadline = state.get_deadline()
            if deadline is not None:
                seconds = self.delay_minutes * 60 if self.delay_minutes else 0
                return deadline + datetime.timedelta(seconds=seconds)
        elif self.trigger == RevealRule.TRIGGER.DEADLINE_ALL:
            latest_deadline = state.get_latest_deadline()
            if latest_deadline is not None:
                seconds = self.delay_minutes * 60 if self.delay_minutes else 0
                return latest_deadline + datetime.timedelta(seconds=seconds)

        return None

    def _is_revealed_due_to_full_points(self, state: 'BaseRevealState') -> bool:
        points = state.get_points()
        max_points = state.get_max_points()
        return points is not None and max_points is not None and points >= max_points

    def _is_revealed_due_to_time(self, state: 'BaseRevealState', time: Optional[datetime.datetime]) -> bool:
        if time is None:
            time = timezone.now()
        reveal_time = self.get_reveal_time(state)
        return reveal_time is not None and time > reveal_time

    def _is_revealed_due_to_max_submissions(self, state: 'BaseRevealState') -> bool:
        submissions = state.get_submissions()
        max_submissions = state.get_max_submissions()
        return submissions is not None and max_submissions is not None and 0 < max_submissions <= submissions
