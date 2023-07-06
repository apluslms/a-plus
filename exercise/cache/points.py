from __future__ import annotations
from dataclasses import dataclass, field, Field, fields, InitVar, MISSING
import datetime
import itertools
from typing import (
    Any,
    cast,
    ClassVar,
    Dict,
    Generic,
    Iterable,
    List,
    Literal,
    Optional,
    overload,
    Type,
    TypeVar,
    Tuple,
    Union,
)

from django.contrib.auth.models import User
from django.db.models.base import Model
from django.db.models.signals import post_save, post_delete, m2m_changed
from django.utils import timezone

from course.models import CourseInstance, CourseModule
from deviations.models import DeadlineRuleDeviation, MaxSubmissionsRuleDeviation, SubmissionRuleDeviation
from lib.cache.cached import CacheBase, DBData, PrecreatedProxies
from lib.helpers import format_points
from notification.models import Notification
from userprofile.models import UserProfile
from .basetypes import (
    add_by_difficulty,
    CachedDataBase,
    CategoryEntryBase,
    EqById,
    ExerciseEntryBase,
    ModuleEntryBase,
    TotalsBase,
)
from .content import CachedContentData
from .hierarchy import ContentMixin
from ..exercise_models import LearningObject
from ..models import BaseExercise, Submission, RevealRule
from ..reveal_states import ExerciseRevealState, ModuleRevealState


T = TypeVar("T")
def upgrade(cls: Type[T], data: Any, kwargs: Dict[str, Any]) -> T:
    """Sets data class to be cls, and sets any missing fields using kwargs and the field defaults"""
    num_base_fields = len(data._dc_fields) # type: ignore
    new_fields = cast(Iterable[Field], cls._dc_fields[num_base_fields:]) # type: ignore

    for field in new_fields:
        if field.name in kwargs:
            setattr(data, field.name, kwargs[field.name])
        elif field.default is not MISSING:
            setattr(data, field.name, field.default)
        elif field.default_factory is not MISSING:
            setattr(data, field.name, field.default_factory())
        else:
            raise TypeError(f"upgrade() missing required argument {field.name}")

    data.__class__ = cls

    return data


def cache_fields(cls):
    """Caches dataclass fields in the _dc_fields attribute of the class"""
    cls._dc_fields = fields(cls)
    for b in cls.__bases__:
        if not hasattr(b, "_dc_fields"):
            try:
                b._dc_fields = fields(b)
            except:
                pass

    return cls


def has_more_points(submission: Submission, current_best_submission: Optional[Submission]) -> bool:
    if current_best_submission is None:
        return True
    if submission.grade == current_best_submission.grade:
        return is_newer(submission, current_best_submission)
    return submission.grade >= current_best_submission.grade


def is_newer(submission: Submission, current_best_submission: Optional[Submission]) -> bool:
    return (
        current_best_submission is None
        or submission.submission_time >= current_best_submission.submission_time
    )


RType = TypeVar("RType")
class RevealableAttribute(Generic[RType]):
    def __set_name__(self, owner, name):
        self.true_name = "_true_" + name
        self.name = "_" + name

    def __get__(self, instance, owner=None) -> RType:
        if instance.feedback_revealed:
            return getattr(instance, self.true_name)
        else:
            return getattr(instance, self.name)


@dataclass(repr=False)
class CommonPointData:
    _is_container: ClassVar[bool] = True
    submission_count: int = 0
    _true_passed: bool = field(default=False, repr=False) # Includes unrevealed data. Use .passed instead.
    _passed: bool = field(default=False, repr=False) # Use .passed instead.
    _true_points: int = field(default=0, repr=False) # Includes unrevealed data. Use .points instead.
    _points: int = field(default=0, repr=False) # Use .points instead.
    feedback_revealed: bool = True

    passed = RevealableAttribute[bool]()
    points = RevealableAttribute[int]()

    @property
    def formatted_points(self) -> str:
        return format_points(self.points, self.feedback_revealed, self._is_container)

    def reveal(self, show_unrevealed: bool = False):
        if show_unrevealed:
            self.feedback_revealed = True


@dataclass(repr=False)
class DifficultyStats(CommonPointData):
    _true_points_by_difficulty: Dict[str, int] = field(default_factory=dict, repr=False)
    _points_by_difficulty: Dict[str, int] = field(default_factory=dict, repr=False)
    _true_unconfirmed_points_by_difficulty: Dict[str, int] = field(default_factory=dict, repr=False)
    _unconfirmed_points_by_difficulty: Dict[str, int] = field(default_factory=dict, repr=False)

    points_by_difficulty = RevealableAttribute[Dict[str, int]]()
    unconfirmed_points_by_difficulty = RevealableAttribute[Dict[str, int]]()


TotalsType = TypeVar("TotalsType", bound=TotalsBase)
@cache_fields
@dataclass
class Totals(DifficultyStats, TotalsBase):
    def as_dict(self):
        revealable = ("passed", "points", "points_by_difficulty", "unconfirmed_points_by_difficulty")
        hide = tuple(k for key in revealable for k in ("_true_" + key, "_" + key))
        out = {
            k: v
            for k,v in self.__dict__.items()
            if k not in hide
        }
        out.update(
            (k, getattr(self, k))
            for k in revealable
        )
        return out

    @classmethod
    def upgrade(cls: Type[TotalsType], data: TotalsBase, **kwargs) -> TotalsType:
        if data.__class__ is cls:
            return cast(cls, data)

        return upgrade(cls, data, kwargs)


CategoryEntryType = TypeVar("CategoryEntryType", bound=CategoryEntryBase)
@cache_fields
@dataclass(eq=False)
class CategoryEntry(DifficultyStats, CategoryEntryBase):
    @classmethod
    def upgrade(cls: Type[CategoryEntryType], data: CategoryEntryBase, **kwargs) -> CategoryEntryType:
        if data.__class__ is cls:
            return cast(cls, data)

        return upgrade(cls, data, kwargs)


ModuleEntryType = TypeVar("ModuleEntryType", bound=ModuleEntryBase)
@cache_fields
@dataclass(eq=False)
class ModuleEntry(DifficultyStats, ModuleEntryBase["ExerciseEntry"]):
    _true_unconfirmed: bool = False
    _unconfirmed: bool = False

    unconfirmed = RevealableAttribute[bool]()

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, data):
        self.__dict__.update(data)

    @classmethod
    def upgrade(cls: Type[ModuleEntryType], data: ModuleEntryBase, **kwargs) -> ModuleEntryType:
        if data.__class__ is cls:
            return cast(cls, data)

        data = upgrade(cls, data, kwargs)

        for child in data.children:
            if child.submittable:
                SubmittableExerciseEntry.upgrade(child)
            else:
                ExerciseEntry.upgrade(child)

        return cast(cls, data)


@dataclass(eq=False)
class SubmissionEntryBase(EqById):
    type: ClassVar[str] = 'submission'
    id: int
    max_points: int
    points_to_pass: int
    confirm_the_level: bool
    graded: bool
    submission_status: Union[str, bool]
    unofficial: bool
    date: datetime.datetime
    url: str
    feedback_reveal_time: Optional[datetime.datetime] = None


@dataclass(eq=False)
class SubmissionEntry(CommonPointData, SubmissionEntryBase):
    _is_container: ClassVar[bool] = False


ExerciseEntryType = TypeVar("ExerciseEntryType", bound=ExerciseEntryBase)
@cache_fields
@dataclass(eq=False, repr=False)
class ExerciseEntry(CommonPointData, ExerciseEntryBase[ModuleEntry, "ExerciseEntry"]):
    _is_container: ClassVar[bool] = False
    _true_unconfirmed: bool = False
    _unconfirmed: bool = False
    is_revealed: bool = True

    unconfirmed = RevealableAttribute[bool]()

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, data):
        self.__dict__.update(data)

    @classmethod
    def upgrade(cls: Type[ExerciseEntryType], data: ExerciseEntryBase, **kwargs) -> ExerciseEntryType:
        if data.__class__ is cls:
            return cast(cls, data)

        data = upgrade(cls, data, kwargs)

        ModuleEntry.upgrade(data.module)

        if data.parent is not None:
            if data.parent.submittable:
                SubmittableExerciseEntry.upgrade(data.parent)
            else:
                ExerciseEntry.upgrade(data.parent)

        for child in data.children:
            if child.submittable:
                SubmittableExerciseEntry.upgrade(child)
            else:
                ExerciseEntry.upgrade(child)

        return cast(cls, data)


@cache_fields
@dataclass(eq=False, repr=False)
class SubmittableExerciseEntry(ExerciseEntry):
    submittable: Literal[True] = True
    submissions: List[SubmissionEntry] = field(default_factory=list)
    _true_best_submission: Optional[int] = None
    _best_submission: Optional[int] = None
    graded: bool = False
    unofficial: bool = False # TODO: this should be True,
    # but we need to ensure nothing breaks when it's changed
    confirmable_points: bool = False
    forced_points: bool = False
    notified: bool = False
    unseen: bool = False
    personal_deadline: Optional[datetime.datetime] = None
    personal_deadline_has_penalty: Optional[bool] = None
    personal_max_submissions: Optional[int] = None
    feedback_reveal_time: Optional[datetime.datetime] = None

    best_submission = RevealableAttribute[Optional[int]]()

    def reveal(self, show_unrevealed: bool):
        super().reveal(show_unrevealed)

        for submission in self.submissions:
            submission.reveal(show_unrevealed)


EitherExerciseEntry = Union[ExerciseEntry, SubmittableExerciseEntry]


CachedPointsDataType = TypeVar("CachedPointsDataType", bound="CachedPointsData")
@cache_fields
@dataclass(eq=False)
class CachedPointsData(CachedDataBase[ModuleEntry, EitherExerciseEntry, CategoryEntry, Totals]):
    PARENTS = ()
    KEY_PREFIX: ClassVar[str] = 'instancepoints'
    NUM_PARAMS: ClassVar[int] = 2
    user_id: InitVar[int]
    invalidate_time: Optional[datetime.datetime] = None
    points_created: datetime.datetime = field(default_factory=timezone.now)

    def __post_init__(self, instance_id: int, user_id: int):
        self._resolved = True
        self._params = (instance_id, user_id)

    def post_build(self, precreated: PrecreatedProxies):
        show_unrevealed = self._modifiers[0]

        for exercise in self.exercise_index.values():
            exercise.reveal(show_unrevealed)

        for module in self.modules:
            module.reveal(show_unrevealed)

        self.total.reveal(show_unrevealed)
        for category in self.categories.values():
            category.reveal(show_unrevealed)

    @classmethod
    def get_for_models(
            cls: Type[CachedPointsDataType],
            instance: CourseInstance,
            user: User,
            show_unrevealed: bool = False,
            prefetch_children: bool = True,
            prefetched_data: Optional[DBData] = None,
            ) -> CachedPointsDataType:
        return cls.get(instance.id, user.id, show_unrevealed, prefetch_children=prefetch_children, prefetched_data=prefetched_data)

    @classmethod
    def get(
            cls: Type[CachedPointsDataType],
            instance_id: int,
            user_id: int,
            show_unrevealed: bool = False,
            prefetch_children: bool = True,
            prefetched_data: Optional[DBData] = None,
            ) -> CachedPointsDataType:
        return super(CachedDataBase, cls).get(instance_id, user_id, modifiers=(show_unrevealed,), prefetch_children=prefetch_children, prefetched_data=prefetched_data)

    def __getstate__(self):
        return self.__dict__

    def __setstate__(self, data):
        self.__dict__.update(data)

    def get_child_proxies(self) -> Iterable[CacheBase]:
        return []

    @classmethod
    def upgrade(cls: Type[CachedPointsDataType], data: CachedDataBase, user_id: Optional[int], **kwargs: Any) -> CachedPointsDataType:
        if data.__class__ is cls:
            return cast(cls, data)

        data = upgrade(cls, data, kwargs)
        data._keys_with_cls = cls._get_keys_with_cls(*data._params)
        data._keys = [row[1:] for row in data._keys_with_cls]
        data._params = (*data._params, user_id)

        for module in data.modules:
            ModuleEntry.upgrade(module)

        for entry in data.exercise_index.values():
            if entry.submittable:
                SubmittableExerciseEntry.upgrade(entry)
            else:
                ExerciseEntry.upgrade(entry)

        for entry in data.categories.values():
            CategoryEntry.upgrade(entry)

        Totals.upgrade(data.total)

        return cast(CachedPointsDataType, data)

    def is_valid(self) -> bool:
        return (
            self.points_created >= self.created
            and (
                self.invalidate_time is None
                or timezone.now() < self.invalidate_time
            )
        )

    def _generate_data(
            self,
            precreated: Optional[PrecreatedProxies] = None,
            prefetched_data: Optional[DBData] = None,
            ):
        # Perform all database queries before generating the cache.
        instance_id, user_id = self._params
        instance = DBData.get_db_object(prefetched_data, CourseInstance, instance_id)

        if user_id is not None:
            user = DBData.get_db_object(prefetched_data, User, user_id)
        else:
            user = None

        if user and user.is_authenticated:
            submissions = list(
                user.userprofile.submissions
                .filter(exercise__course_module__course_instance=instance)
                .select_related()
                .prefetch_related('exercise__parent', 'exercise__submission_feedback_reveal_rule', 'notifications')
                .only('id', 'exercise', 'submission_time', 'status', 'grade', 'force_exercise_points')
                .order_by('exercise', '-submission_time')
            )
            exercises = BaseExercise.objects.filter(course_module__course_instance=instance)
            deadline_deviations = list(
                DeadlineRuleDeviation.objects
                .get_max_deviations(user.userprofile, exercises)
            )
            submission_deviations = list(
                MaxSubmissionsRuleDeviation.objects
                .get_max_deviations(user.userprofile, exercises)
            )
            module_instances = list(
                instance.course_modules.all()
            )
        else:
            submissions = []
            deadline_deviations = []
            submission_deviations = []
            module_instances = []

        content = CachedContentData.get(instance_id)
        # "upgrade" the type of content to CachedPointsData.
        # This replaces each object in the data with the CachedPointsData version
        # while retaining any common object references (e.g. module.children and
        # exercise_index values refer to the same object instances)
        base_points_data = CachedPointsData.upgrade(content, user_id)

        data = self._generate_data_internal(
            base_points_data,
            user is not None and user.is_authenticated,
            submissions,
            deadline_deviations,
            submission_deviations,
            module_instances,
        )

        # Pick the lowest invalidate_time if it is duplicated.
        invalidate_time = data.invalidate_time
        if isinstance(invalidate_time, tuple):
            if invalidate_time[0] is not None:
                if invalidate_time[1] is not None:
                    data.invalidate_time = min(invalidate_time)
                else:
                    data.invalidate_time = invalidate_time[0]
            else:
                data.invalidate_time = invalidate_time[1]

        data.points_created = timezone.now()

        for base in reversed(CachedPointsData._parents):
            for name in base._cached_fields:
                self.__dict__[name] = data.__dict__[name]

    @classmethod
    def _generate_data_internal( # noqa: MC0001
            cls,
            data: CachedPointsData,
            is_authenticated: bool,
            all_submissions: Iterable[Submission],
            deadline_deviations: Iterable[DeadlineRuleDeviation],
            submission_deviations: Iterable[MaxSubmissionsRuleDeviation],
            module_instances: Iterable[CourseModule],
            ) -> CachedPointsData:
        """
        Handles the generation of one version of the cache (staff or student).
        All source data is prefetched by `_generate_data` and provided as
        arguments to this method.
        """
        exercise_index = data.exercise_index
        modules = data.modules
        categories = data.categories
        total = data.total

        if is_authenticated:
            # Augment deviation data.
            for deviation in deadline_deviations:
                try:
                    # deviation.exercise is a BaseExercise (i.e. submittable)
                    entry = cast(SubmittableExerciseEntry, exercise_index[deviation.exercise.id])
                except KeyError:
                    continue
                entry.personal_deadline = (
                    entry.closing_time + datetime.timedelta(minutes=deviation.extra_minutes)
                )
                entry.personal_deadline_has_penalty = not deviation.without_late_penalty

            for deviation in submission_deviations:
                try:
                    # deviation.exercise is a BaseExercise (i.e. submittable)
                    entry = cast(SubmittableExerciseEntry, exercise_index[deviation.exercise.id])
                except KeyError:
                    continue
                entry.personal_max_submissions = (
                    entry.max_submissions + deviation.extra_submissions
                )

            def update_invalidation_time(invalidate_time: Optional[datetime.datetime]) -> None:
                if (
                    invalidate_time is not None
                    and invalidate_time > timezone.now()
                    and (
                        data.invalidate_time is None
                        or invalidate_time < data.invalidate_time
                    )
                ):
                    data.invalidate_time = invalidate_time

            def apply_reveal_rule(
                    data: CachedPointsData,
                    entry: SubmittableExerciseEntry,
                    reveal_rule: RevealRule,
                    last_submission: Submission
                    ) -> None:
                """
                Evaluate the reveal rule of the current exercise and ensure
                that feedback is hidden appropriately.
                """
                state = ExerciseRevealState(entry)
                is_revealed = reveal_rule.is_revealed(state)
                reveal_time = reveal_rule.get_reveal_time(state)

                if is_revealed:
                    entry._best_submission = entry._true_best_submission
                    entry._points = entry._true_points
                    entry._passed = entry._true_passed
                else:
                    entry._best_submission = last_submission.id
                    entry._points = 0

                entry.feedback_revealed = is_revealed
                entry.feedback_reveal_time = reveal_time

                for submission in entry.submissions:
                    if is_revealed:
                        submission._points = submission._true_points
                        submission._passed = submission._true_passed
                    else:
                        submission._points = 0
                    submission.feedback_revealed = is_revealed
                    submission.feedback_reveal_time = reveal_time

                # If the reveal rule depends on time, update the cache's
                # invalidation time.
                update_invalidation_time(reveal_time)

            # Augment submission data.
            # The submissions are ordered by exercise, so we can use groupby
            for (exercise, submissions) in itertools.groupby(all_submissions, key=lambda o: o.exercise):
                final_submission = None
                last_submission = None

                try:
                    entry = cast(SubmittableExerciseEntry, exercise_index[exercise.id])
                except KeyError:
                    continue

                if exercise.grading_mode == BaseExercise.GRADING_MODE.BEST:
                    is_better_than = has_more_points
                elif exercise.grading_mode == BaseExercise.GRADING_MODE.LAST:
                    is_better_than = is_newer
                else:
                    is_better_than = has_more_points

                for submission in submissions:
                    ready = submission.status == Submission.STATUS.READY
                    unofficial = submission.status == Submission.STATUS.UNOFFICIAL
                    if ready or submission.status in (Submission.STATUS.WAITING, Submission.STATUS.INITIALIZED):
                        entry.submission_count += 1
                    entry.submissions.append(
                        SubmissionEntry(
                            id = submission.id,
                            max_points = entry.max_points,
                            points_to_pass = entry.points_to_pass,
                            confirm_the_level = entry.confirm_the_level,
                            submission_count = 1, # to fool points badge
                            _true_passed = submission.grade >= entry.points_to_pass,
                            _true_points = submission.grade,
                            graded = submission.is_graded, # TODO: should this be official (is_graded = ready or unofficial)
                            submission_status = submission.status if not submission.is_graded else False,
                            unofficial = unofficial,
                            date = submission.submission_time,
                            url = submission.get_url('submission-plain'),
                            feedback_revealed = True,
                            feedback_reveal_time = None,
                        )
                    )
                    # Update best submission if exercise points are not forced, and
                    # one of these is true:
                    # 1) current submission in ready (thus is not unofficial) AND
                    #    a) current best is an unofficial OR
                    #    b) current submission is better depending on grading mode
                    # 2) All of:
                    #    - current submission is unofficial AND
                    #    - current best is unofficial
                    #    - current submission is better depending on grading mode
                    if submission.force_exercise_points:
                        # This submission is chosen as the final submission and no
                        # further submissions are considered.
                        entry._true_best_submission = submission.id
                        entry._true_passed = ready and submission.grade >= entry.points_to_pass
                        entry._true_points = submission.grade
                        entry.graded = True
                        entry.unofficial = False
                        entry.forced_points = True

                        final_submission = submission
                    if not entry.forced_points:
                        if ( # pylint: disable=too-many-boolean-expressions
                            ready and (
                                entry.unofficial or
                                is_better_than(submission, final_submission)
                            )
                        ) or (
                            unofficial and
                            not entry.graded and # NOTE: == entry.unofficial,
                            # but before any submissions entry.unofficial is False
                            is_better_than(submission, final_submission)
                        ):
                            entry._true_best_submission = submission.id
                            entry._true_passed = ready and submission.grade >= entry.points_to_pass
                            entry._true_points = submission.grade
                            entry.graded = ready # != unofficial
                            entry.unofficial = unofficial

                            final_submission = submission
                    # Update last_submission to be the last submission, or the last
                    # official submission if there are any official submissions.
                    # Note that the submissions are ordered by descendng time.
                    if last_submission is None or (
                        last_submission.status == Submission.STATUS.UNOFFICIAL
                        and not unofficial
                    ):
                        last_submission = submission
                    if submission.notifications.exists():
                        entry.notified = True
                        if submission.notifications.filter(seen=False).exists():
                            entry.unseen = True

                # Check the reveal rule now that all submissions for the exercise have been iterated.
                # last_submission is never None here but this appeases the typing system.
                if last_submission is not None:
                    reveal_rule = exercise.active_submission_feedback_reveal_rule
                    apply_reveal_rule(data, entry, reveal_rule, last_submission)

        if not show_unrevealed:
            def update_is_revealed_recursive(entry: Dict[str, Any], is_revealed: bool) -> None:
                if is_revealed:
                    return
                entry.is_revealed = is_revealed
                for child in entry.children:
                    update_is_revealed_recursive(child, is_revealed)

            for module in module_instances:
                model_chapter = module.model_answer
                if model_chapter is None:
                    continue
                reveal_rule = module.active_model_solution_reveal_rule
                entry = exercise_index[model_chapter.id]
                cached_module = module_index[module.id]
                state = ModuleRevealState(cached_module)
                is_revealed = reveal_rule.is_revealed(state)
                reveal_time = reveal_rule.get_reveal_time(state)
                update_is_revealed_recursive(entry, is_revealed)
                update_invalidation_time(reveal_time)

        # Unconfirm points.
        for entry in exercise_index.values():
            if (
                entry.submittable
                and entry.confirm_the_level
                and not entry._true_passed
            ):
                parent = entry.parent
                if parent is None:
                    parent = entry.module
                parent._true_unconfirmed = True
                for child in parent.children:
                    child._true_unconfirmed = True

            if (
                entry.submittable
                and entry.confirm_the_level
                and not entry._passed
            ):
                parent = entry.parent
                if parent is None:
                    parent = entry.module
                parent._unconfirmed = True
                for child in parent.children:
                    child._unconfirmed = True

        # Collect points and check limits.
        def add_to(target: Union[ModuleEntry, CategoryEntry, Totals], entry: SubmittableExerciseEntry) -> None:
            target.submission_count += entry.submission_count
            target.feedback_revealed = target.feedback_revealed and entry.feedback_revealed
            # NOTE: entry can be only ready or unofficial (exercise level
            # points are only copied, only if submission is in ready or
            # unofficial state)
            if entry.unofficial:
                pass
            # thus, all points are now ready..
            else:
                if entry._true_unconfirmed:
                    add_by_difficulty(
                        target._true_unconfirmed_points_by_difficulty,
                        entry.difficulty,
                        entry._true_points,
                    )
                # and finally, only remaining points are official (not unofficial & not unconfirmed)
                else:
                    target._true_points += entry._true_points
                    add_by_difficulty(
                        target._true_points_by_difficulty,
                        entry.difficulty,
                        entry._true_points,
                    )

                if entry._unconfirmed:
                    add_by_difficulty(
                        target._unconfirmed_points_by_difficulty,
                        entry.difficulty,
                        entry._points,
                    )
                # and finally, only remaining points are official (not unofficial & not unconfirmed)
                else:
                    target._points += entry._points
                    add_by_difficulty(
                        target._points_by_difficulty,
                        entry.difficulty,
                        entry._points,
                    )

        def r_collect(
                module: ModuleEntry,
                parent: Optional[EitherExerciseEntry],
                children: List[EitherExerciseEntry],
                ) -> Tuple[bool, bool, bool]:
            _true_passed = True
            _passed = True
            is_revealed = True
            max_points = 0
            submissions = 0
            _true_points = 0
            _points = 0
            confirm_entry: Optional[SubmittableExerciseEntry] = None
            for entry in children:
                if isinstance(entry, SubmittableExerciseEntry):
                    # TODO: this seems to skip counting points and submission for
                    # exercises with confirm_the_level = True
                    if entry.confirm_the_level:
                        confirm_entry = entry
                    else:
                        _true_passed = _true_passed and entry._true_passed
                        _passed = _passed and entry._passed
                        is_revealed = is_revealed and entry.feedback_revealed
                        max_points += entry.max_points
                        submissions += entry.submission_count
                        if entry.graded:
                            _true_points += entry._true_points
                            _points += entry._points
                            add_to(module, entry)
                            add_to(categories[entry.category_id], entry)
                            add_to(total, entry)
                r_passed, r_true_passed, r_is_revealed = r_collect(module, entry, entry.children)
                _true_passed = r_true_passed and _true_passed
                _passed = r_passed and _passed
                is_revealed = r_is_revealed and is_revealed
            if confirm_entry and submissions > 0:
                confirm_entry.confirmable_points = True
            if parent and not parent.submittable:
                parent.max_points = max_points
                parent.submission_count = submissions
                parent._true_passed = _true_passed
                parent._passed = _passed
                parent._true_points = _true_points
                parent._points = _points
            return _passed, _true_passed, is_revealed
        for module in modules:
            r_passed, r_true_passed, _ = r_collect(module, None, module.children)
            module._true_passed = (
                r_true_passed
                and module._true_points >= module.points_to_pass
            )
            module._passed = (
                r_passed
                and module._points >= module.points_to_pass
            )
        for category in categories.values():
            category._true_passed = category._true_points >= category.points_to_pass
            category._passed = category._points >= category.points_to_pass

        return data


class CachedPoints(ContentMixin[ModuleEntry, EitherExerciseEntry, CategoryEntry, Totals]):
    """
    Extends `CachedContent` to include data about a user's submissions and
    points in the course's exercises.

    Note that the `data` returned by this is dependent on the `show_unrevealed`
    parameter. When `show_unrevealed` is `False`, reveal rules are respected and
    exercise results are hidden when the reveal rule does not evaluate to true.
    When `show_unrevealed` is `True`, reveal rules are ignored and the results are
    always revealed.
    """
    KEY_PREFIX = 'points'
    data: CachedPointsData

    def __init__(
            self,
            course_instance: CourseInstance,
            user: User,
            show_unrevealed: bool = False,
            ) -> None:
        self.instance = course_instance
        self.user = user
        self.data = CachedPointsData.get_for_models(course_instance, user, show_unrevealed)

    def created(self) -> Tuple[datetime.datetime, datetime.datetime]:
        return self.data.points_created, super().created()

    def submission_ids( # pylint: disable=too-many-arguments
            self,
            number: Optional[str] = None,
            category_id: Optional[int] = None,
            module_id: Optional[int] = None,
            exercise_id: Optional[int] = None,
            filter_for_assistant: bool = False,
            best: bool = True,
            fallback_to_last: bool = False,
            raise_404=True,
            ) -> List[int]:
        exercises = self.search_exercises(
            number=number,
            category_id=category_id,
            module_id=module_id,
            exercise_id=exercise_id,
            filter_for_assistant=filter_for_assistant,
            raise_404=raise_404,
        )
        submissions = []
        if best:
            for entry in exercises:
                if not isinstance(entry, SubmittableExerciseEntry):
                    continue

                if entry.best_submission is not None:
                    submissions.append(entry.best_submission)
                elif fallback_to_last:
                    entry_submissions = entry.submissions
                    if entry_submissions:
                        submissions.append(entry_submissions[0].id) # Last submission is first in the cache
        else:
            for entry in exercises:
                if not isinstance(entry, SubmittableExerciseEntry):
                    continue

                submissions.extend(s.id for s in entry.submissions)
        return submissions

    @overload
    def entry_for_exercise(self, model: BaseExercise) -> SubmittableExerciseEntry: ...
    @overload
    def entry_for_exercise(self, model: LearningObject) -> EitherExerciseEntry: ...
    def entry_for_exercise(self, model: LearningObject) -> EitherExerciseEntry:
        return super().entry_for_exercise(model)

    @classmethod
    def invalidate(cls, *models):
        CachedPointsData.invalidate(*models)


# pylint: disable-next=unused-argument
def invalidate_content(sender: Type[Model], instance: Submission, **kwargs: Any) -> None:
    course = instance.exercise.course_instance
    for profile in instance.submitters.all():
        CachedPoints.invalidate(course, profile.user)

def invalidate_content_m2m( # pylint: disable=too-many-arguments
        sender: Type[Model], # pylint: disable=unused-argument
        instance: Union[Submission, UserProfile],
        action: str,
        reverse: bool,
        model: Type[Model],
        pk_set: Iterable[int],
        **kwargs: Any,
        ) -> None:
    # many-to-many field Submission.submitters may be modified without
    # triggering the Submission post save hook
    if action not in ('post_add', 'pre_remove'):
        return
    if reverse:
        # instance is a UserProfile
        if model == Submission:
            seen_courses = set()
            for submission_pk in pk_set:
                try:
                    submission = Submission.objects.get(pk=submission_pk)
                    course_instance = submission.exercise.course_instance
                    if course_instance.pk not in seen_courses:
                        CachedPoints.invalidate(course_instance, instance.user)
                    else:
                        seen_courses.add(course_instance.pk)
                except Submission.DoesNotExist:
                    pass
    else:
        # instance is a Submission
        invalidate_content(Submission, instance)
# pylint: disable-next=unused-argument
def invalidate_notification(sender: Type[Model], instance: Notification, **kwargs: Any) -> None:
    course = instance.course_instance
    if not course and instance.submission:
        course = instance.submission.exercise.course_instance
    CachedPoints.invalidate(course, instance.recipient.user)
# pylint: disable-next=unused-argument
def invalidate_deviation(sender: Type[Model], instance: SubmissionRuleDeviation, **kwargs: Any) -> None:
    # Invalidate for the student who received the deviation as well as all
    # students who have submitted this exercise with them.
    course = instance.exercise.course_instance
    CachedPoints.invalidate(course, instance.submitter.user)
    submitters = UserProfile.objects.filter(
        submissions__exercise=instance.exercise,
        submissions__submitters=instance.submitter
    ).distinct()
    for profile in submitters:
        if profile != instance.submitter:
            CachedPoints.invalidate(course, profile.user)
# pylint: disable-next=unused-argument
def invalidate_submission_reveal(sender: Type[Model], instance: RevealRule, **kwargs: Any) -> None:
    # Invalidate for all students who have submitted the exercise whose
    # submission feedback reveal rule changed.
    try:
        exercise = BaseExercise.objects.get(submission_feedback_reveal_rule=instance)
    except BaseExercise.DoesNotExist:
        return
    course = exercise.course_instance
    submitters = UserProfile.objects.filter(submissions__exercise=exercise).distinct()
    for profile in submitters:
        CachedPoints.invalidate(course, profile.user)


# Automatically invalidate cached points when submissions change.
post_save.connect(invalidate_content, sender=Submission)
post_delete.connect(invalidate_content, sender=Submission)
post_save.connect(invalidate_notification, sender=Notification)
post_delete.connect(invalidate_notification, sender=Notification)
post_save.connect(invalidate_deviation, sender=DeadlineRuleDeviation)
post_delete.connect(invalidate_deviation, sender=DeadlineRuleDeviation)
post_save.connect(invalidate_deviation, sender=MaxSubmissionsRuleDeviation)
post_delete.connect(invalidate_deviation, sender=MaxSubmissionsRuleDeviation)
post_save.connect(invalidate_submission_reveal, sender=RevealRule)
post_delete.connect(invalidate_submission_reveal, sender=RevealRule)
# listen to the m2m_changed signal since submission.submitters is a many-to-many
# field and instances must be saved before the many-to-many fields may be modified,
# that is to say, the submission post save hook may see an empty submitters list
m2m_changed.connect(invalidate_content_m2m, sender=Submission.submitters.through)
