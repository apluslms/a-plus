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

    trigger = models.IntegerField(choices=TRIGGER.choices,
        verbose_name=_('LABEL_TRIGGER'))
    delay_minutes = models.IntegerField(blank=True, null=True,
        verbose_name=_('LABEL_DELAY_MINUTES'))
    time = models.DateTimeField(blank=True, null=True,
        verbose_name=_('LABEL_TIME'))
    currently_revealed = models.BooleanField(default=False,
        verbose_name=_('LABEL_CURRENTLY_REVEALED'))

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
            RevealRule.TRIGGER.DEADLINE_ALL
        ]:
            if time is None:
                time = timezone.now()
            reveal_time = self.get_reveal_time(state)
            if reveal_time is not None:
                return time > reveal_time
        elif self.trigger == RevealRule.TRIGGER.COMPLETION:
            points = state.get_points()
            max_points = state.get_max_points()
            if points is not None and max_points is not None:
                if points >= max_points:
                    return True
            submissions = state.get_submissions()
            max_submissions = state.get_max_submissions()
            if submissions is not None and max_submissions is not None:
                if max_submissions == 0:
                    return False
                if submissions >= max_submissions:
                    return True

        return False

    def get_reveal_time(self, state: 'BaseRevealState') -> Optional[datetime.datetime]:
        """
        Returns the time at which `is_reveal` will be true, or `None` if the
        time is indeterminate (depends on actions such as the student
        completing the exercise).
        """

        if self.trigger == RevealRule.TRIGGER.TIME:
            return self.time
        if self.trigger == RevealRule.TRIGGER.DEADLINE:
            deadline = state.get_deadline()
            if deadline is not None:
                return deadline + datetime.timedelta(minutes=self.delay_minutes or 0)
        elif self.trigger == RevealRule.TRIGGER.DEADLINE_ALL:
            latest_deadline = state.get_latest_deadline()
            if latest_deadline is not None:
                return latest_deadline + datetime.timedelta(minutes=self.delay_minutes or 0)

        return None
