import datetime
from typing import Any, Dict, List, Optional, overload, Union

from django.contrib.auth.models import User

from .exercise_models import BaseExercise


class BaseRevealState:
    """
    An object that provides all necessary data for evaluating a reveal rule.
    All functions are unimplemented and return `None`. Subclass this and
    override the functions that your subclass supports.
    """
    def get_points(self) -> Optional[int]:
        return None

    def get_max_points(self) -> Optional[int]:
        return None

    def get_submissions(self) -> Optional[int]:
        return None

    def get_max_submissions(self) -> Optional[int]:
        return None

    def get_deadline(self) -> Optional[datetime.datetime]:
        return None

    def get_latest_deadline(self) -> Optional[datetime.datetime]:
        return None


class ExerciseRevealState(BaseRevealState):
    """
    BaseRevealState implementation for BaseExercise. Most of the data is
    retrieved from the CachedPoints cache.
    """
    @overload
    def __init__(self, exercise: BaseExercise, student: User): ...
    @overload
    def __init__(self, exercise: Dict[str, Any]): ...
    def __init__(
            self,
            exercise: Union[BaseExercise, Dict[str, Any]],
            student: Optional[User] = None
            ):
        # Can be constructed either with a BaseExercise instance or a
        # CachedPoints exercise entry. If a BaseExercise is provided, the
        # cache entry is fetched here.
        if isinstance(exercise, BaseExercise):
            from .cache.content import CachedContent
            from .cache.points import CachedPoints
            cached_content = CachedContent(exercise.course_instance)
            # 'True' is always passed to CachedPoints as the is_staff argument
            # because we need to know the actual points.
            cached_points = CachedPoints(exercise.course_instance, student, cached_content, True)
            entry,_,_,_ = cached_points.find(exercise)
            self.cache = entry
        else:
            self.cache = exercise

    def get_points(self) -> Optional[int]:
        return self.cache['points']

    def get_max_points(self) -> Optional[int]:
        return self.cache['max_points']

    def get_submissions(self) -> Optional[int]:
        return self.cache['submission_count']

    def get_max_submissions(self) -> Optional[int]:
        personal_max_submissions = self.cache['personal_max_submissions']
        if personal_max_submissions is not None:
            return personal_max_submissions
        return self.cache['max_submissions']

    def get_deadline(self) -> Optional[datetime.datetime]:
        deadlines = self._get_common_deadlines()
        personal_deadline = self.cache['personal_deadline']
        if personal_deadline is not None:
            deadlines.append(personal_deadline)
        return max(deadlines)

    def get_latest_deadline(self) -> Optional[datetime.datetime]:
        deadlines = self._get_common_deadlines()
        exercise = BaseExercise.objects.get(id=self.cache['id'])
        # This is the only thing that we don't get from the cache.
        # Caching this could be considered.
        deviation = exercise.deadlineruledeviation_set.order_by('-extra_minutes').first()
        if deviation is not None:
            deadlines.append(deviation.get_new_deadline())
        return max(deadlines)

    def _get_common_deadlines(self) -> List[datetime.datetime]:
        deadlines = [self.cache['closing_time']]
        if self.cache['late_allowed'] and self.cache['late_percent'] > 0:
            deadlines.append(self.cache['late_time'])
        return deadlines
