from __future__ import annotations
import datetime
from typing import List, Optional, overload, TYPE_CHECKING, Union

from django.contrib.auth.models import User

from deviations.models import DeadlineRuleDeviation
from course.models import CourseModule
from .cache.content import CachedContent
from .exercise_models import BaseExercise

if TYPE_CHECKING:
    from .cache.points import ExerciseEntry, ModuleEntry, SubmittableExerciseEntry


def _get_exercise_common_deadlines(exercise: SubmittableExerciseEntry) -> List[datetime.datetime]:
    deadlines = [exercise.closing_time]
    if exercise.late_allowed and exercise.late_percent > 0:
        deadlines.append(exercise.late_time)
    return deadlines


def _get_exercise_deadline(exercise: SubmittableExerciseEntry) -> datetime.datetime:
    deadlines = _get_exercise_common_deadlines(exercise)
    personal_deadline = exercise.personal_deadline
    if personal_deadline is not None:
        deadlines.append(personal_deadline)
    return max(deadlines)


def _get_max_submissions(exercise: SubmittableExerciseEntry) -> int:
    personal_max_submissions = exercise.personal_max_submissions
    if personal_max_submissions is not None:
        return personal_max_submissions
    return exercise.max_submissions


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
    def __init__(self, exercise: BaseExercise, student: User):
        ...
    @overload
    def __init__(self, exercise: SubmittableExerciseEntry):
        ...
    def __init__(
            self,
            exercise: Union[BaseExercise, SubmittableExerciseEntry],
            student: Optional[User] = None
            ):
        # Can be constructed either with a BaseExercise instance or a
        # CachedPoints exercise entry. If a BaseExercise is provided, the
        # cache entry is fetched here.
        if isinstance(exercise, BaseExercise):
            from .cache.points import CachedPoints # pylint: disable=import-outside-toplevel
            cached_content = CachedContent(exercise.course_instance)
            # 'True' is always passed to CachedPoints as the show_unrevealed argument
            # because we need to know the actual points.
            cached_points = CachedPoints(exercise.course_instance, student, cached_content, True)
            entry,_,_,_ = cached_points.find(exercise)
            self.cache = entry
        else:
            self.cache = exercise

        self.max_deviation_fetched: bool = False
        self.max_deviation: Optional[DeadlineRuleDeviation] = None

    def get_points(self) -> Optional[int]:
        return self.cache.points

    def get_max_points(self) -> Optional[int]:
        return self.cache.max_points

    def get_submissions(self) -> Optional[int]:
        return self.cache.submission_count

    def get_max_submissions(self) -> Optional[int]:
        return _get_max_submissions(self.cache)

    def get_deadline(self) -> Optional[datetime.datetime]:
        return _get_exercise_deadline(self.cache)

    def get_latest_deadline(self) -> Optional[datetime.datetime]:
        deadlines = self._get_common_deadlines()
        # This is the only thing that we don't get from CachedPoints. It is
        # cached within this object, though, so it won't have to be fetched
        # again if RevealRule.is_revealed and RevealRule.get_reveal_time are
        # called separately.
        if not self.max_deviation_fetched:
            self.max_deviation = (
                DeadlineRuleDeviation.objects
                .filter(exercise_id=self.cache.id)
                .order_by('-extra_minutes').first()
            )
            self.max_deviation_fetched = True
        if self.max_deviation is not None:
            deadlines.append(self.max_deviation.get_new_deadline(self.cache.closing_time))
        return max(deadlines)

    def _get_common_deadlines(self) -> List[datetime.datetime]:
        return _get_exercise_common_deadlines(self.cache)


class ModuleRevealState(BaseRevealState):
    @overload
    def __init__(self, module: CourseModule, student: User):
        ...
    @overload
    def __init__(self, module: ModuleEntry):
        ...
    def __init__(self, module: Union[CourseModule, ModuleEntry], student: Optional[User] = None):
        if isinstance(module, CourseModule):
            from .cache.points import CachedPoints # pylint: disable=import-outside-toplevel
            cached_content = CachedContent(module.course_instance)
            cached_points = CachedPoints(module.course_instance, student, cached_content, True)
            self.module_id = module.id
            cached_module, _, _, _ = cached_points.find(module)
            self.module = cached_module
        else:
            self.module_id = module.id
            self.module = module
        self.exercises = self._get_exercises()
        self.max_deviation_fetched: bool = False
        self.max_deviation: Optional[DeadlineRuleDeviation] = None

    def get_deadline(self) -> Optional[datetime.datetime]:
        return max(_get_exercise_deadline(exercise) for exercise in self.exercises)

    def get_latest_deadline(self) -> Optional[datetime.datetime]:
        deadlines = []
        exercise_dict = {}
        for exercise in self.exercises:
            deadlines.extend(_get_exercise_common_deadlines(exercise))
            exercise_dict[exercise.id] = exercise
        if not self.max_deviation_fetched:
            self.max_deviation = (
                DeadlineRuleDeviation.objects
                .filter(exercise__course_module_id=self.module_id)
                .order_by('-extra_minutes').first()
            )
            self.max_deviation_fetched = True
        if self.max_deviation is not None:
            deadlines.append(
                self.max_deviation.get_new_deadline(exercise_dict[self.max_deviation.exercise_id].closing_time)
            )
        return max(deadlines)

    def get_points(self) -> Optional[int]:
        points = sum(exercise.points for exercise in self.exercises)
        return points

    def get_max_points(self) -> Optional[int]:
        return self.module.max_points

    def get_submissions(self) -> Optional[int]:
        return sum(min(exercise.submission_count, _get_max_submissions(exercise)) for exercise in self.exercises)

    def get_max_submissions(self) -> Optional[int]:
        return sum(_get_max_submissions(exercise) for exercise in self.exercises)

    def _get_exercises(self) -> List[SubmittableExerciseEntry]:
        from .cache.points import SubmittableExerciseEntry # pylint: disable=import-outside-toplevel
        exercises: List[SubmittableExerciseEntry] = []

        def recursion(children: List[ExerciseEntry]) -> None:
            for entry in children:
                if isinstance(entry, SubmittableExerciseEntry):
                    exercises.append(entry)
                recursion(entry.children)

        recursion(self.module.children)
        return exercises
