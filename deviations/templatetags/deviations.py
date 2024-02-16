import datetime
from typing import Optional

from django import template

from ..models import DeadlineRuleDeviation


register = template.Library()


@register.simple_tag
def new_deviation_seconds(
        deviation: DeadlineRuleDeviation,
        seconds: Optional[int],
        date: Optional[datetime.datetime]
        ) -> int:
    """
    Get the extra seconds for a deadline deviation after being overridden.
    """
    if date:
        return deviation.exercise.delta_in_seconds_from_closing_to_date(date)
    return seconds


@register.simple_tag
def new_deviation_date(
        deviation: DeadlineRuleDeviation,
        seconds: Optional[int],
        date: Optional[datetime.datetime]
        ) -> datetime.datetime:
    """
    Get the new deadline for a deadline deviation after being overridden.
    """
    if date:
        return date
    return deviation.exercise.course_module.closing_time + datetime.timedelta(seconds=seconds)
