from __future__ import annotations
from dataclasses import dataclass, field, Field, fields, InitVar, MISSING
import datetime
from itertools import groupby
from typing import (
    Any,
    cast,
    ClassVar,
    Dict,
    Generic,
    Iterable,
    List,
    Optional,
    overload,
    Set,
    Type,
    TypeVar,
    Tuple,
    Union,
)

from django.contrib.auth.models import User
from django.db.models import prefetch_related_objects
from django.db.models.signals import post_save, post_delete, pre_delete, m2m_changed
from django.utils import timezone

from course.models import CourseInstance, CourseModule, StudentGroup, StudentModuleGoal
from deviations.models import DeadlineRuleDeviation, MaxSubmissionsRuleDeviation
from lib.cache.cached import DBDataManager, Dependencies, ProxyManager, resolve_proxies
from lib.helpers import format_points
from notification.models import Notification
from .basetypes import (
    add_by_difficulty,
    CachedDataBase,
    CategoryEntryBase,
    EqById,
    LearningObjectEntryBase,
    ModuleEntryBase,
    TotalsBase,
)
from .hierarchy import ContentMixin
from .invalidate_util import (
    m2m_submission_userprofile,
    model_exercise_as_iterable,
    model_exercise_siblings_confirms_the_level,
    model_module,
    with_user_ids,
)
from ..exercise_models import LearningObject
from ..models import BaseExercise, Submission, SubmissionProto, RevealRule
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
            except TypeError:
                pass

    return cls


def none_min(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a and b:
        return min(a,b)
    return a or b

def next_timestamp(timestamps) -> Optional[float]:
    now = timezone.now().timestamp()
    future_timestamps = [ts for ts in timestamps if ts and ts > now]
    return min(timestamps) if future_timestamps else None


def _add_to(target: Union[ModulePoints, CategoryPoints, Totals], entry: ExercisePoints) -> None:
    target.feedback_revealed = target.feedback_revealed and entry.feedback_revealed

    if not entry.graded:
        return

    target.submission_count += entry.submission_count
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


class PointsDBData(DBDataManager):
    exercises: Dict[int, Set[int]]
    modules: Set[int]
    submissions: Dict[Tuple[int, int], List[Submission]]
    deadline_deviations: Dict[Tuple[int, int], List[DeadlineRuleDeviation]]
    submission_deviations: Dict[Tuple[int, int], List[MaxSubmissionsRuleDeviation]]
    reveal_rules: Dict[int, RevealRule]
    module_reveal_rules: Dict[int, RevealRule]
    groups: Dict[Tuple[int, int], List[StudentGroup]]
    fetched: Set[Tuple[int,int]]

    def __init__(self):
        self.exercises = {}
        self.modules = set()
        self.submissions = {}
        self.deadline_deviations = {}
        self.submission_deviations = {}
        self.reveal_rules = {}
        self.module_reveal_rules = {}
        self.groups = {}
        self.fetched = set()

    def add(self, proxy: Union[CachedPointsData, ModulePoints, LearningObjectPoints]) -> None:
        model_id, user_id = proxy._params
        if user_id is not None and isinstance(proxy, LearningObjectPoints) and (user_id, model_id) not in self.fetched:
            self.exercises.setdefault(user_id, set()).add(model_id)
        elif isinstance(proxy, ModulePoints):
            self.modules.add(model_id)

    def fetch(self) -> None:
        modules = (
            CourseModule.objects
            .filter(id__in=self.modules, model_answer__isnull=False)
            .select_related(None)
            .select_related("model_solution_reveal_rule")
            .only("id", "model_solution_reveal_rule")
        )
        self.module_reveal_rules.update(
            (m.id, m.active_model_solution_reveal_rule)
            for m in modules
        )
        self.modules.clear()

        for user_id, exercise_ids in self.exercises.items():
            self.fetched.update((user_id, exercise_id) for exercise_id in exercise_ids)

            user = User.objects.get(id=user_id)
            submissions = (
                Submission.objects
                .filter(submitters=user.userprofile, exercise_id__in=exercise_ids)
                .prefetch_related("exercise", "notifications", "submitters")
                .order_by('exercise_id', '-submission_time')
            )
            for exercise_id, exercise_submissions in groupby(submissions, key=lambda s: s.exercise_id):
                self.submissions[(user_id, exercise_id)] = list(exercise_submissions)

            deadline_deviations = (
                DeadlineRuleDeviation.objects
                .get_max_deviations(user.userprofile, exercise_ids)
            )
            for exercise_id, exercise_deviations in groupby(deadline_deviations, key=lambda s: s.exercise_id):
                self.deadline_deviations[(user_id, exercise_id)] = list(exercise_deviations)
            submission_deviations = (
                MaxSubmissionsRuleDeviation.objects
                .get_max_deviations(user.userprofile, exercise_ids)
            )
            for exercise_id, exercise_deviations in groupby(submission_deviations, key=lambda s: s.exercise_id):
                self.submission_deviations[(user_id, exercise_id)] = list(exercise_deviations)

            exercises = (
                BaseExercise.bare_objects
                .filter(id__in=exercise_ids)
                .select_related("submission_feedback_reveal_rule", "course_module")
                .only("id", "course_module__course_instance_id", "submission_feedback_reveal_rule")
            )

            self.reveal_rules.update(
                (e.id, e.active_submission_feedback_reveal_rule)
                for e in exercises
            )

            instance_ids = {e.course_module.course_instance_id for e in exercises}
            group_qs = StudentGroup.objects.filter(
                course_instance__in=instance_ids, members=user.userprofile
            ).prefetch_related("members").order_by('course_instance_id')
            instance_groups = {
                instance_id: list(groups)
                for instance_id, groups in groupby(group_qs, lambda g: g.course_instance_id)
            }
            self.groups.update(
                ((user_id, e.id), instance_groups.get(e.course_module.course_instance_id, []))
                for e in exercises
            )

        self.exercises.clear()

    def get_submissions(self, user_id: int, exercise_id: int) -> List[Submission]:
        return self.submissions.get((user_id, exercise_id), [])

    def get_deadline_deviations(self, user_id: int, exercise_id: int) -> List[DeadlineRuleDeviation]:
        return self.deadline_deviations.get((user_id, exercise_id), [])

    def get_submission_deviations(self, user_id: int, exercise_id: int) -> List[MaxSubmissionsRuleDeviation]:
        return self.submission_deviations.get((user_id, exercise_id), [])

    def get_reveal_rule(self, exercise_id: int) -> RevealRule:
        return self.reveal_rules[exercise_id]

    def get_module_reveal_rule(self, module_id: int) -> Optional[RevealRule]:
        return self.module_reveal_rules.get(module_id)

    def get_groups(self, user_id: int, exercise_id: int) -> List[StudentGroup]:
        return self.groups[(user_id, exercise_id)]


RType = TypeVar("RType")
class RevealableAttribute(Generic[RType]):
    def __set_name__(self, owner, name):
        self.true_name = "_true_" + name
        self.name = "_" + name

    def __get__(self, instance, owner=None) -> RType:
        if instance.feedback_revealed:
            return getattr(instance, self.true_name)
        return getattr(instance, self.name)


@dataclass(repr=False)
class CommonPointData:
    _is_container: ClassVar[bool] = True
    submission_count: int = 0
    _true_passed: bool = field(default=False, repr=False) # Includes unrevealed info. Use .passed instead.
    _passed: bool = field(default=False, repr=False) # Use .passed instead.
    _true_points: int = field(default=0, repr=False) # Includes unrevealed info. Use .points instead.
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
class CategoryPoints(DifficultyStats, CategoryEntryBase):
    @classmethod
    def upgrade(cls: Type[CategoryEntryType], data: CategoryEntryBase, **kwargs) -> CategoryEntryType:
        if data.__class__ is cls:
            return cast(cls, data)

        return upgrade(cls, data, kwargs)


@dataclass(eq=False)
class SubmissionEntryBase(SubmissionProto, EqById):
    type: ClassVar[str] = 'submission'
    id: int
    exercise: ExercisePoints
    max_points: int
    points_to_pass: int
    confirm_the_level: bool
    graded: bool
    status: str
    unofficial: bool
    unofficial_submission_type: Optional[str]
    date: datetime.datetime
    url: str
    hash: Optional[str]
    force_exercise_points: bool
    is_assessed: bool
    late_penalty_applied: Optional[float]
    group_id: int
    feedback_reveal_time: Optional[datetime.datetime]


@dataclass(eq=False)
class SubmissionEntry(CommonPointData, SubmissionEntryBase):
    _is_container: ClassVar[bool] = False


ExerciseEntryType = TypeVar("ExerciseEntryType", bound="LearningObjectPoints")
class LearningObjectPoints(CommonPointData, LearningObjectEntryBase["ModulePoints", "LearningObjectPoints"]):
    KEY_PREFIX = "exercisepoints"
    NUM_PARAMS = 2
    INVALIDATORS = [
        (Submission, [post_delete, post_save], with_user_ids(model_exercise_as_iterable)),
        (DeadlineRuleDeviation, [post_delete, post_save], with_user_ids(model_exercise_as_iterable)),
        (MaxSubmissionsRuleDeviation, [post_delete, post_save], with_user_ids(model_exercise_as_iterable)),
        (RevealRule, [post_delete, post_save], with_user_ids(model_exercise_as_iterable)),
        # listen to the m2m_changed signal since submission.submitters is a many-to-many
        # field and instances must be saved before the many-to-many fields may be modified,
        # that is to say, the submission post save hook may see an empty submitters list
        (Submission.submitters.through, [m2m_changed], m2m_submission_userprofile(model_exercise_as_iterable))
    ]
    DBCLS = PointsDBData
    _is_container: ClassVar[bool] = False
    _true_children_unconfirmed: bool
    _children_unconfirmed: bool
    # This is different in ExerciseEntry compared to ExerciseEntryBase, so we need
    # to save it separately for ExerciseEntry
    max_points: int
    confirmable_children: bool

    children_unconfirmed = RevealableAttribute[bool]()

    @property
    def unconfirmed(self) -> bool:
        if self.parent:
            return self.parent.children_unconfirmed
        return self.module.children_unconfirmed

    @property
    def is_revealed(self) -> bool:
        if self.parent is not None and not self.parent.is_revealed:
            return False

        return all(entry.is_model_answer_revealed for entry in self.model_answer_modules)

    @property
    def _true_unconfirmed(self) -> bool:
        if self.parent:
            return self.parent._true_children_unconfirmed
        return self.module._true_children_unconfirmed

    @property
    def _unconfirmed(self) -> bool:
        if self.parent:
            return self.parent._children_unconfirmed
        return self.module._children_unconfirmed

    @classmethod
    def get( # pylint: disable=arguments-differ
            cls: Type[ExerciseEntryType],
            lobj: Union[LearningObject, int],
            user: Union[User, int, None],
            show_unrevealed: bool = False,
            prefetch_children: bool = False,
            ) -> ExerciseEntryType:
        return super()._get(
            params=cls.parameter_ids(lobj, user),
            modifiers=(show_unrevealed,),
            prefetch_children=prefetch_children,
        )

    @classmethod
    def get_many(
            cls: Type[ExerciseEntryType],
            exercises: Iterable[Union[LearningObject, int]],
            user: Union[User, int, None],
            show_unrevealed: bool = False,
            ) -> Iterable[ExerciseEntryType]:
        if not isinstance(user, int):
            user = user.id
        exercises = [ex if isinstance(ex, int) else ex.id for ex in exercises]
        proxies = [cls.proxy(ex, user, modifiers=(show_unrevealed,)) for ex in exercises]
        resolve_proxies(proxies)
        return proxies

    def post_build(self, precreated: ProxyManager):
        self.reveal(self._modifiers[0])

        if isinstance(self.module, ModulePoints):
            return

        user_id = self._params[1]
        modifiers = self._modifiers

        self.module = precreated.get_or_create_proxy(ModulePoints, *self.module._params, user_id, modifiers=modifiers)

        self.model_answer_modules = [
            precreated.get_or_create_proxy(ModulePoints, *module._params, user_id, modifiers=modifiers)
            for module in self.model_answer_modules
        ]

        if self.parent:
            self.parent = precreated.get_or_create_proxy(
                LearningObjectPoints, *self.parent._params, user_id, modifiers=modifiers
            )

        children = self.children
        for i, params in enumerate(children):
            children[i] = precreated.get_or_create_proxy(
                LearningObjectPoints, *params._params, user_id, modifiers=modifiers
            )

    def get_proxy_keys(self) -> Iterable[str]:
        return super().get_proxy_keys() + ["model_answer_modules"]

    def _generate_common(
            self,
            precreated: ProxyManager,
            ):
        user_id = self._params[1]

        self.module = precreated.get_or_create_proxy(
            ModulePoints, *self.module._params, user_id, modifiers=self._modifiers
        )
        if self.parent is not None:
            self.parent = precreated.get_or_create_proxy(
                LearningObjectPoints, *self.parent._params, user_id, modifiers=self._modifiers
            )
        else:
            self.parent = None
        self.children = [
            precreated.get_or_create_proxy(LearningObjectPoints, *entry._params, user_id, modifiers=self._modifiers)
            for entry in self.children
        ]
        self.model_answer_modules = [
            precreated.get_or_create_proxy(ModulePoints, *entry._params, user_id, modifiers=self._modifiers)
            for entry in self.model_answer_modules
        ]

        if any(not s._resolved for s in self.children):
            precreated.resolve(self.children)

        must_confirm = any(entry.confirm_the_level for entry in self.children)

        self._true_children_unconfirmed = must_confirm
        self._children_unconfirmed = must_confirm

        self.confirmable_children = False
        for entry in self.children:
            if not entry.confirm_the_level and entry.submission_count > 0:
                self.confirmable_children = True

    def _generate_data(
            self,
            precreated: ProxyManager,
            prefetched_data: LearningObjectPoints.DBCLS,
            ) -> Optional[Dependencies]:
        if self.submittable:
            self.__class__ = ExercisePoints
            return self._generate_data(precreated, prefetched_data)

        self._generate_common(precreated)

        self._true_passed = True
        self._passed = True
        self.submission_count = 0
        self.feedback_revealed = True
        self.max_points = 0
        self._true_points = 0
        self._points = 0
        for entry in self.children:
            if entry.confirm_the_level:
                self._true_children_unconfirmed = self._true_children_unconfirmed and not entry._true_passed
                self._children_unconfirmed = self._children_unconfirmed and not entry._passed
            elif entry.is_visible():
                self.feedback_revealed = self.feedback_revealed and entry.feedback_revealed
                self.max_points += entry.max_points
                self.submission_count += entry.submission_count
                self._expires_on = none_min(self._expires_on, entry._expires_on)
                # pylint: disable-next=unidiomatic-typecheck
                if type(entry) is LearningObjectPoints or entry.graded:
                    self._true_points += entry._true_points
                    self._points += entry._points

        return {
            LearningObjectEntryBase: [self._params[:1]],
            LearningObjectPoints: [proxy._params for proxy in self.children],
        }


class ExercisePoints(LearningObjectPoints):
    # Remove LearningObjectPoints from the parents. ExercisePoints isn't built
    # on top of LearningObjectPoints but has its fields. Inheriting directly from LearningObjectPoints
    # allows isinstance(..., LearningObjectPoints) to work
    PARENTS = LearningObjectPoints._parents[:-1]
    KEY_PREFIX = LearningObjectPoints.KEY_PREFIX
    NUM_PARAMS = LearningObjectPoints.NUM_PARAMS
    INVALIDATORS = [
        # LearningObjectPoints handles the general learning object invalidation. Here we invalidate for reasons
        # specific to submittable exercises.
        # These invalidate exercises with confirm_the_level = True whenever any of its sibling exercises change
        (Submission, [post_delete, post_save], with_user_ids(model_exercise_siblings_confirms_the_level)),
        (DeadlineRuleDeviation, [post_delete, post_save], with_user_ids(model_exercise_siblings_confirms_the_level)),
        (
            MaxSubmissionsRuleDeviation,
            [post_delete, post_save],
            with_user_ids(model_exercise_siblings_confirms_the_level)
        ),
        (RevealRule, [post_delete, post_save], with_user_ids(model_exercise_siblings_confirms_the_level)),
        (Notification, [post_delete, post_save], with_user_ids(model_exercise_as_iterable)),
        (Notification, [post_delete, post_save], with_user_ids(model_exercise_siblings_confirms_the_level)),
    ]
    DBCLS = LearningObjectPoints.DBCLS
    # field() works because LearningObjectPoints inherits CommonPointData, which is a dataclass
    submissions: List[SubmissionEntry] = field(default_factory=list) #pylint: disable=invalid-field-call
    _true_best_submission: Optional[SubmissionEntry]
    _best_submission: Optional[SubmissionEntry]
    graded: bool
    unofficial: bool
    unofficial_submission_type: Optional[str]
    forced_points: bool
    notified: bool
    unseen: bool
    personal_deadline: Optional[datetime.datetime]
    personal_deadline_has_penalty: Optional[bool]
    personal_max_submissions: Optional[int]
    feedback_reveal_time: Optional[datetime.datetime]
    show_zero_points_immediately: Optional[bool]

    best_submission = RevealableAttribute[Optional[SubmissionEntry]]()

    @property
    def official_points(self) -> int:
        return self.best_submission.points if self.best_submission and not self.unofficial else 0

    @property
    def confirmable_points(self) -> bool:
        if self.parent is not None:
            return self.confirm_the_level and self.parent.confirmable_children
        return self.confirm_the_level and self.module.confirmable_children

    def get_penalty(self) -> Optional[float]:
        return self.best_submission.late_penalty_applied if self.best_submission else None

    def get_group_id(self) -> Optional[int]:
        if self.submission_count > 0:
            s = self.submissions[0]
            return s.group_id
        return None

    @classmethod
    def get(cls, # pylint: disable=arguments-renamed
            exercise: Union[BaseExercise, int],
            user: Union[User, int, None],
            show_unrevealed: bool = False,
            prefetch_children: bool = False,
            ) -> ExercisePoints:
        return super()._get(
            params=cls.parameter_ids(exercise, user),
            modifiers=(show_unrevealed,),
            prefetch_children=prefetch_children,
        )

    def post_build(self, precreated: ProxyManager):
        super().post_build(precreated)
        for submission in self.submissions:
            if not self.show_zero_points_immediately:
                submission.reveal(self._modifiers[0])
            else:
                if submission._true_points == 0:
                    submission.feedback_revealed = True

    # pylint: disable-next=too-many-locals
    def _generate_data( # noqa: MC0001
            self,
            precreated: ProxyManager,
            prefetched_data: ExercisePoints.DBCLS,
            ) -> Optional[Dependencies]:
        if not self.submittable:
            self.__class__ = LearningObjectPoints
            return self._generate_data(precreated, prefetched_data)

        self._generate_common(precreated)

        lobj_id, user_id = self._params[:2]

        if user_id is not None:
            submissions = prefetched_data.get_submissions(user_id, lobj_id)
            deadline_deviations = prefetched_data.get_deadline_deviations(user_id, lobj_id)
            submission_deviations = prefetched_data.get_submission_deviations(user_id, lobj_id)
            groups = prefetched_data.get_groups(user_id, lobj_id)
        else:
            submissions = []
            deadline_deviations = []
            submission_deviations = []
            groups = []

        self.personal_deadline = None
        self.personal_deadline_has_penalty = None
        for deviation in deadline_deviations:
            self.personal_deadline = (
                self.closing_time + datetime.timedelta(seconds=deviation.extra_seconds)
            )
            self.personal_deadline_has_penalty = not deviation.without_late_penalty

        self.personal_max_submissions = None
        for deviation in submission_deviations:
            self.personal_max_submissions = (
                self.max_submissions + deviation.extra_submissions
            )

        self.submission_count = 0
        self._true_passed = self.points_to_pass == 0
        self._passed = self.points_to_pass == 0
        self._true_points = 0
        self.submittable = True
        self.submissions = []
        self._true_best_submission = None
        self._best_submission = None
        self.graded = False
        self.unofficial = False # TODO: this should be True,
        # but we need to ensure nothing breaks when it's changed
        self.unofficial_submission_type = None
        self.forced_points = False
        self.notified = False
        self.unseen = False
        self.model_answer_modules = []
        self.show_zero_points_immediately = False

        # Augment submission data.
        final_submission = None
        last_submission = None

        if self.grading_mode == BaseExercise.GRADING_MODE.BEST:
            is_better_than = has_more_points
        elif self.grading_mode == BaseExercise.GRADING_MODE.LAST:
            is_better_than = is_newer
        else:
            is_better_than = has_more_points

        for submission in submissions:
            ready = submission.status == Submission.STATUS.READY
            unofficial = submission.status == Submission.STATUS.UNOFFICIAL
            if ready or submission.status in (Submission.STATUS.WAITING, Submission.STATUS.INITIALIZED):
                self.submission_count += 1

            if isinstance(submission.meta_data, dict):
                submission_hash = str(submission.meta_data.get("hash"))
            else:
                submission_hash = None

            group = None
            if submission.submitters.exists():
                group = StudentGroup.get_exact_from(
                    groups,
                    submission.submitters.all(),
                )

            if group is not None:
                group_id = group.id
            else:
                group_id = 0
            submission_entry = SubmissionEntry(
                id = submission.id,
                exercise = self,
                max_points = self.max_points,
                points_to_pass = self.points_to_pass,
                confirm_the_level = self.confirm_the_level,
                submission_count = 1, # to fool points badge
                _true_passed = submission.grade >= self.points_to_pass,
                _true_points = submission.grade,
                graded = submission.is_graded,
                status = submission.status,
                unofficial = unofficial,
                unofficial_submission_type = submission.unofficial_submission_type,
                date = submission.submission_time,
                url = submission.get_url('submission-plain'),
                feedback_revealed = True,
                feedback_reveal_time = None,
                hash = submission_hash,
                force_exercise_points = submission.force_exercise_points,
                is_assessed = submission.is_assessed,
                late_penalty_applied = submission.late_penalty_applied,
                group_id = group_id,
            )
            self.submissions.append(submission_entry)
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
                self._true_best_submission = submission_entry
                self._true_passed = ready and submission.grade >= self.points_to_pass
                self._true_points = submission.grade
                self.graded = True
                self.unofficial = False
                self.forced_points = True

                final_submission = submission
            if not self.forced_points:
                if ( # pylint: disable=too-many-boolean-expressions
                    ready and (
                        self.unofficial or
                        is_better_than(submission, final_submission)
                    )
                ) or (
                    unofficial and
                    not self.graded and # NOTE: == entry.unofficial,
                    # but before any submissions entry.unofficial is False
                    is_better_than(submission, final_submission)
                ):
                    self._true_best_submission = submission_entry
                    self._true_passed = ready and submission.grade >= self.points_to_pass
                    self._true_points = submission.grade
                    self.graded = ready # != unofficial
                    self.unofficial = unofficial

                    final_submission = submission
            # Update last_submission to be the last submission, or the last
            # official submission if there are any official submissions.
            # Note that the submissions are ordered by descendng time.
            if last_submission is None or (
                last_submission.unofficial
                and not unofficial
            ):
                last_submission = submission_entry
            if submission.notifications.exists():
                self.notified = True
                if submission.notifications.filter(seen=False).exists():
                    self.unseen = True

        # These need to be set here to make sure that ExerciseRevealState below works correctly
        self._best_submission = self._true_best_submission
        self._points = self._true_points
        self._passed = self._true_passed

        if self.submissions:
            # Check the reveal rule now that all submissions for the exercise have been iterated.
            reveal_rule = prefetched_data.get_reveal_rule(lobj_id)
            state = ExerciseRevealState(self)
            self.show_zero_points_immediately = reveal_rule.show_zero_points_immediately
            is_revealed = reveal_rule.is_revealed(state)
            reveal_time = reveal_rule.get_reveal_time(state)
        else:
            # Do not hide points if no submissions have been made
            is_revealed = True
            reveal_time = None

        timestamp = reveal_time and reveal_time.timestamp()

        if not is_revealed:
            self._best_submission = last_submission
            self._points = 0
            self._passed = False

        self.feedback_revealed = is_revealed
        self.feedback_reveal_time = reveal_time
        self._expires_on = timestamp

        for submission in self.submissions:
            if is_revealed:
                submission._points = submission._true_points
                self._passed = self._true_passed
            else:
                submission._points = 0
                self._passed = False
            submission.feedback_revealed = is_revealed
            submission.feedback_reveal_time = reveal_time

        return {
            LearningObjectEntryBase: [self._params[:1]],
            LearningObjectPoints: [proxy._params for proxy in self.children],
        }


EitherExerciseEntry = Union[LearningObjectPoints, ExercisePoints]


ModuleEntryType = TypeVar("ModuleEntryType", bound="ModulePoints")
class ModulePoints(DifficultyStats, ModuleEntryBase[LearningObjectPoints]):
    KEY_PREFIX = "modulepoints"
    NUM_PARAMS = 2
    INVALIDATORS = [
        (RevealRule, [post_delete, post_save], with_user_ids(model_module)),
    ]
    DBCLS = PointsDBData
    _true_children_unconfirmed: bool
    _children_unconfirmed: bool
    is_model_answer_revealed: bool
    confirmable_children: bool
    module_goal_points: Optional[int]

    children_unconfirmed = RevealableAttribute[bool]()

    @classmethod
    def get( # pylint: disable=arguments-differ
            cls: Type[ModuleEntryType],
            module: Union[CourseModule, int],
            user: Union[User, int, None],
            show_unrevealed: bool = False,
            prefetch_children: bool = False,
            ) -> ModuleEntryType:
        return super()._get(
            params=cls.parameter_ids(module, user),
            modifiers=(show_unrevealed,),
            prefetch_children=prefetch_children,
        )

    def post_build(self, precreated: ProxyManager):
        self.reveal(self._modifiers[0])

        if isinstance(self.instance, CachedPointsData):
            return

        user_id = self._params[1]
        modifiers = self._modifiers

        self.instance = precreated.get_or_create_proxy(
            CachedPointsData, *self.instance._params, user_id, modifiers=modifiers
        )

        children = self.children
        for i, params in enumerate(children):
            children[i] = precreated.get_or_create_proxy(
                LearningObjectPoints, *params._params, user_id, modifiers=modifiers
            )

    def _generate_data(
            self,
            precreated: ProxyManager,
            prefetched_data: ModulePoints.DBCLS,
            ) -> Optional[Dependencies]:
        module_id, user_id = self._params[:2]

        self.submissions = 0
        self.submission_count = 0
        self._true_passed = True
        self._passed = True
        self._true_points = 0
        self._points = 0
        self.feedback_revealed = True
        self._true_points_by_difficulty = {}
        self._points_by_difficulty = {}
        self._true_unconfirmed_points_by_difficulty = {}
        self._unconfirmed_points_by_difficulty = {}
        self.module_goal_points = None
        self.instance = precreated.get_or_create_proxy(
            CachedPointsData, *self.instance._params, user_id, modifiers=self._modifiers
        )
        self.children = [
            precreated.get_or_create_proxy(LearningObjectPoints, *entry._params, user_id, modifiers=self._modifiers)
            for entry in self.children
        ]
        precreated.resolve(self.children, depth=-1)

        must_confirm = any(entry.confirm_the_level for entry in self.children)
        self._true_children_unconfirmed = must_confirm
        self._children_unconfirmed = must_confirm
        self.confirmable_children = False
        for entry in self.children:
            if entry.confirm_the_level:
                self._true_children_unconfirmed = self._true_children_unconfirmed and not entry._true_passed
                self._children_unconfirmed = self._children_unconfirmed and not entry._passed
            elif entry.submission_count > 0:
                self.confirmable_children = True

        try:
            user = User.objects.get(id=user_id)
            student_module_goal = StudentModuleGoal.objects.get(module_id=module_id, student_id=user.userprofile)
            self.module_goal_points = student_module_goal.goal_points
        except StudentModuleGoal.DoesNotExist:
            pass
        except User.DoesNotExist:
            pass

        def add_points(children):
            for entry in children:
                if not entry.confirm_the_level and isinstance(entry, ExercisePoints) and entry.is_visible():
                    self._expires_on = none_min(self._expires_on, entry._expires_on)
                    _add_to(self, entry)
                add_points(entry.children)

        add_points(self.children)
        self._true_passed = self._true_passed and self._true_points >= self.points_to_pass
        self._passed = self._passed and self._points >= self.points_to_pass

        reveal_rule = prefetched_data.get_module_reveal_rule(module_id)
        if reveal_rule is None:
            self.is_model_answer_revealed = True
        else:
            state = ModuleRevealState(self)
            self.is_model_answer_revealed = reveal_rule.is_revealed(state) and not self.instance.is_on_lifesupport
            reveal_time = reveal_rule.get_reveal_time(state)
            reveal_rule_timestamp = reveal_time and reveal_time.timestamp()
            self._expires_on = next_timestamp([reveal_rule_timestamp, self.instance.lifesupport_start.timestamp()])

        return {
            ModuleEntryBase: [self._params[:1]],
            LearningObjectPoints: [proxy._params for proxy in self.children],
        }


CachedPointsDataType = TypeVar("CachedPointsDataType", bound="CachedPointsData")
class CachedPointsData(CachedDataBase[ModulePoints, EitherExerciseEntry, CategoryPoints, Totals]):
    KEY_PREFIX: ClassVar[str] = 'instancepoints'
    NUM_PARAMS: ClassVar[int] = 2
    INVALIDATORS = []
    user_id: InitVar[int]
    points_created: datetime.datetime
    categories: Dict[int, CategoryPoints]
    total: Totals

    def post_build(self, precreated: ProxyManager):
        show_unrevealed = self._modifiers[0]
        self.total.reveal(show_unrevealed)
        for category in self.categories.values():
            category.reveal(show_unrevealed)

        if not self.modules or isinstance(self.modules[0], ModulePoints):
            return

        user_id = self._params[1]
        modifiers = self._modifiers

        modules = self.modules
        module_index = self.module_index
        for i, entry in enumerate(modules):
            proxy = precreated.get_or_create_proxy(ModulePoints, *entry._params, user_id, modifiers=modifiers)
            modules[i] = proxy
            module_index[entry._params[0]] = proxy

        exercise_index = self.exercise_index
        for k, entry in exercise_index.items():
            exercise_index[k] = precreated.get_or_create_proxy(
                LearningObjectPoints, *entry._params, user_id, modifiers=modifiers
            )

    @classmethod
    def get( # pylint: disable=arguments-renamed
            cls: Type[CachedPointsDataType],
            instance: Union[CourseInstance, int],
            user: Union[User, int, None],
            show_unrevealed: bool = False,
            prefetch_children: bool = True,
            ) -> CachedPointsDataType:
        return super()._get(
            params=cls.parameter_ids(instance, user),
            modifiers=(show_unrevealed,),
            prefetch_children=prefetch_children,
        )

    def _generate_data(
            self,
            precreated: ProxyManager,
            prefetched_data: CachedPointsData.DBCLS,
            ) -> Optional[Dependencies]:
        user_id = self._params[1]

        for category in self.categories.values():
            CategoryPoints.upgrade(category)
        Totals.upgrade(self.total)

        self.exercise_index = {
            id: precreated.get_or_create_proxy(LearningObjectPoints, id, user_id, modifiers=self._modifiers)
            for id in self.exercise_index
        }

        self.modules = [
            precreated.get_or_create_proxy(ModulePoints, *module._params, user_id, modifiers=self._modifiers)
            for module in self.modules
        ]

        self.module_index = {
            module._params[0]: module
            for module in self.modules
        }

        precreated.resolve(self.get_child_proxies())

        for entry in self.exercise_index.values():
            if not entry.confirm_the_level and isinstance(entry, ExercisePoints) and entry.is_visible():
                self._expires_on = none_min(self._expires_on, entry._expires_on)
                _add_to(self.categories[entry.category_id], entry)
                _add_to(self.total, entry)

        for category in self.categories.values():
            category._true_passed = category._true_points >= category.points_to_pass
            category._passed = category._points >= category.points_to_pass

        self.points_created = timezone.now()

        # We rely on a ModuleEntry being invalid if any of the exercises are
        return {
            CachedDataBase: [self._params[:1]],
            ModulePoints: [proxy._params for proxy in self.modules],
        }


class CachedPoints(ContentMixin[ModulePoints, EitherExerciseEntry, CategoryPoints, Totals]):
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
            prefetch_children: bool = True,
            ) -> None:
        self.instance = course_instance
        self.user = user
        self.data = CachedPointsData.get(course_instance, user, show_unrevealed, prefetch_children=prefetch_children)

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
                if not isinstance(entry, ExercisePoints):
                    continue

                if entry.best_submission is not None:
                    submissions.append(entry.best_submission.id)
                elif fallback_to_last:
                    entry_submissions = entry.submissions
                    if entry_submissions:
                        submissions.append(entry_submissions[0].id) # Last submission is first in the cache
        else:
            for entry in exercises:
                if not isinstance(entry, ExercisePoints):
                    continue

                submissions.extend(s.id for s in entry.submissions)
        return submissions

    @overload
    def entry_for_exercise(self, model: BaseExercise) -> ExercisePoints:
        ...
    @overload
    def entry_for_exercise(self, model: LearningObject) -> EitherExerciseEntry:
        ...
    def entry_for_exercise(self, model: LearningObject) -> EitherExerciseEntry:
        return super().entry_for_exercise(model)

    @classmethod
    def invalidate(cls, instance: CourseInstance, user: User):
        CachedPointsData.invalidate(instance, user)
        for module in instance.course_modules.prefetch_related("learning_objects").all():
            ModuleEntryBase.invalidate(module, user)
            for exercise in module.learning_objects.all():
                LearningObjectEntryBase.invalidate(exercise, user)


# Required so that Submission post_delete receivers can access submitters
# pylint: disable-next=unused-argument
def prefetch_submitters(sender: Type[Submission], instance: Submission, **kwargs: Any) -> None:
    prefetch_related_objects([instance], "submitters")


# Required so that RevealRule post_delete receivers can access exercise
# pylint: disable-next=unused-argument
def prefetch_exercise(sender: Type[RevealRule], instance: RevealRule, **kwargs: Any) -> None:
    try:
        instance.exercise = BaseExercise.objects.get(submission_feedback_reveal_rule=instance)
    except BaseExercise.DoesNotExist:
        instance.exercise = None


# Required so that RevealRule post_delete receivers can access module
# pylint: disable-next=unused-argument
def prefetch_module(sender: Type[RevealRule], instance: RevealRule, **kwargs: Any) -> None:
    try:
        instance.module = CourseModule.objects.get(model_solution_reveal_rule=instance)
    except CourseModule.DoesNotExist:
        instance.module = None


pre_delete.connect(prefetch_submitters, Submission)
pre_delete.connect(prefetch_exercise, RevealRule)
pre_delete.connect(prefetch_module, RevealRule)
