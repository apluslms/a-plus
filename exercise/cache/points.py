from __future__ import annotations
from dataclasses import dataclass, field, Field, fields, InitVar, MISSING
import datetime
from time import time
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
    Type,
    TypeVar,
    Tuple,
    Union,
)

from django.contrib.auth.models import User
from django.db.models import prefetch_related_objects, Prefetch
from django.db.models.signals import post_save, post_delete, pre_delete, m2m_changed
from django.utils import timezone

from course.models import CourseInstance, CourseModule
from deviations.models import DeadlineRuleDeviation, MaxSubmissionsRuleDeviation
from lib.cache.cached import CacheBase, DBData, ProxyManager
from lib.helpers import format_points
from notification.models import Notification
from .basetypes import (
    add_by_difficulty,
    CachedDataBase,
    CategoryEntryBase,
    EqById,
    ExerciseEntryBase,
    ModuleEntryBase,
    TotalsBase,
)
from .hierarchy import ContentMixin
from .invalidate_util import (
    m2m_submission_userprofile,
    model_exercise_module_id,
    model_instance_id,
    model_exercise_ancestors,
    model_exercise_siblings_confirms_the_level,
    model_module_id,
    with_user_ids,
)
from ..exercise_models import CourseChapter, LearningObject
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


def none_min(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a and b:
        return min(a,b)
    return a or b


def _add_to(target: Union[ModuleEntry, CategoryEntry, Totals], entry: SubmittableExerciseEntry) -> None:
    target._true_passed = target._true_passed and entry._true_passed
    target._passed = target._passed and entry._passed
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


def prefetch_exercise_data(
        prefetched_data: DBData,
        user: Optional[User],
        lobjs: Iterable[LearningObject],
        ) -> None:
    exercise_objs = [lobj for lobj in lobjs if isinstance(lobj, BaseExercise)]
    prefetch_related_objects(exercise_objs, "submission_feedback_reveal_rule")

    if user is not None:
        submission_queryset = (
            user.userprofile.submissions
            .prefetch_related("notifications")
            .only('id', 'exercise', 'submission_time', 'status', 'grade', 'force_exercise_points', 'grader_id', 'meta_data', 'late_penalty_applied')
            .order_by('-submission_time')
        )

        # SubmittableExerciseEntry relies on these only containing the max deviations
        # for the user for whom cache is being generated
        deadline_deviations = (
            DeadlineRuleDeviation.objects
            .get_max_deviations(user.userprofile, exercise_objs)
        )
        submission_deviations = (
            MaxSubmissionsRuleDeviation.objects
            .get_max_deviations(user.userprofile, exercise_objs)
        )

        prefetched_data.add(user)
        prefetched_data.extend(DeadlineRuleDeviation, deadline_deviations)
        prefetched_data.extend(MaxSubmissionsRuleDeviation, submission_deviations)
    else:
        submission_queryset = Submission.objects.none()
        deadline_deviations = []
        submission_deviations = []

    prefetch_related_objects(
        exercise_objs,
        Prefetch("submissions", submission_queryset)
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

    def reset_points(self):
        self.submission_count = 0
        self._true_passed = False
        self._passed = False
        self._true_points = 0
        self._points = 0
        self.feedback_revealed = True


@dataclass(repr=False)
class DifficultyStats(CommonPointData):
    _true_points_by_difficulty: Dict[str, int] = field(default_factory=dict, repr=False)
    _points_by_difficulty: Dict[str, int] = field(default_factory=dict, repr=False)
    _true_unconfirmed_points_by_difficulty: Dict[str, int] = field(default_factory=dict, repr=False)
    _unconfirmed_points_by_difficulty: Dict[str, int] = field(default_factory=dict, repr=False)

    points_by_difficulty = RevealableAttribute[Dict[str, int]]()
    unconfirmed_points_by_difficulty = RevealableAttribute[Dict[str, int]]()

    def reset_points(self):
        super().reset_points()
        self._true_points_by_difficulty = {}
        self._points_by_difficulty = {}
        self._true_unconfirmed_points_by_difficulty = {}
        self._unconfirmed_points_by_difficulty = {}


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
class ExerciseEntry(CommonPointData, ExerciseEntryBase["ModuleEntry", "ExerciseEntry"]):
    KEY_PREFIX = "exercisepoints"
    NUM_PARAMS = 2
    INVALIDATORS = [
        (Submission, [post_delete, post_save], with_user_ids(model_exercise_ancestors)),
        (DeadlineRuleDeviation, [post_delete, post_save], with_user_ids(model_exercise_ancestors)),
        (MaxSubmissionsRuleDeviation, [post_delete, post_save], with_user_ids(model_exercise_ancestors)),
        (RevealRule, [post_delete, post_save], with_user_ids(model_exercise_ancestors)),
        (Submission.submitters.through, [m2m_changed], m2m_submission_userprofile(model_exercise_ancestors))
    ]
    _is_container: ClassVar[bool] = False
    _true_children_unconfirmed: bool
    _children_unconfirmed: bool
    model_answer_modules: List["ModuleEntry"]
    invalidate_time: Optional[float]
    # This is different in ExerciseEntry compared to ExerciseEntryBase, so we need
    # to save it separately for ExerciseEntry
    max_points: int

    children_unconfirmed = RevealableAttribute[bool]()

    @property
    def unconfirmed(self) -> bool:
        if self.parent:
            return self.parent.children_unconfirmed
        else:
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
        else:
            return self.module._true_children_unconfirmed

    @property
    def _unconfirmed(self) -> bool:
        if self.parent:
            return self.parent._children_unconfirmed
        else:
            return self.module._children_unconfirmed

    def post_build(self, precreated: ProxyManager):
        self.reveal(self._modifiers[0])

        if not isinstance(self.module, tuple):
            return

        user_id = self._params[1]
        modifiers = self._modifiers

        self.module = precreated.get_or_create_proxy(ModuleEntry, *self.module[0], user_id, modifiers=modifiers)

        self.model_answer_modules = [
            precreated.get_or_create_proxy(ModuleEntry, *params[0], user_id, modifiers=modifiers)
            for params in self.model_answer_modules
        ]

        if self.parent:
            self.parent = precreated.get_or_create_proxy(ExerciseEntry, *self.parent[0], user_id, modifiers=modifiers)

        children = self.children
        for i, params in enumerate(children):
            children[i] = precreated.get_or_create_proxy(ExerciseEntry, *params[0], user_id, modifiers=modifiers)

    def get_proxy_keys(self) -> Iterable[str]:
        return super().get_proxy_keys() + ["model_answer_modules"]

    def is_valid(self) -> bool:
        return (
            self.invalidate_time is None
            or time() >= self.invalidate_time
        )

    def _prefetch_data(self, prefetched_data: Optional[DBData]) -> Tuple[DBData, LearningObject, Optional[User], Iterable[LearningObject], Iterable[LearningObject]]:
        lobj_id, user_id = self._params[:2]
        lobj = DBData.get_db_object(prefetched_data, LearningObject, lobj_id)
        if user_id is None:
            user = None
        else:
            user = DBData.get_db_object(prefetched_data, User, user_id)

        if not prefetched_data:
            prefetched_data = DBData()

            module = lobj.course_module
            module_lobjs = module.learning_objects.all()

            prefetched_data.add(module)
            prefetched_data.extend(LearningObject, module_lobjs)

            prefetch_exercise_data(prefetched_data, user, module_lobjs)

            # This is needed so that prefetch_exercise_data affects lobj
            lobj = prefetched_data.get_db_object(LearningObject, lobj_id)
        else:
            module_lobjs = prefetched_data.filter_db_objects(LearningObject, course_module_id=lobj.course_module_id)

        child_lobjs = prefetched_data.filter_db_objects(LearningObject, parent_id=lobj.id)

        return prefetched_data, lobj, user, module_lobjs, child_lobjs

    def _generate_common(self, precreated: ProxyManager, prefetched_data: DBData, lobj, module_lobjs, child_lobjs):
        user_id = self._params[1]

        self.module = precreated.get_or_create_proxy(ModuleEntry, lobj.course_module_id, user_id, modifiers=self._modifiers)
        if lobj.parent:
            self.parent = precreated.get_or_create_proxy(ExerciseEntry, lobj.parent_id, user_id, modifiers=self._modifiers)
        else:
            self.parent = None
        self.children = [precreated.get_or_create_proxy(ExerciseEntry, o.id, user_id, modifiers=self._modifiers) for o in child_lobjs]
        if isinstance(lobj, CourseChapter):
            self.model_answer_modules = [
                precreated.get_or_create_proxy(ModuleEntry, module.id, user_id, modifiers=self._modifiers)
                for module in lobj.model_answer_modules.all()
            ]
        else:
            self.model_answer_modules = []

        if any(not s._resolved for s in self.children):
            # Create proxies for all the module learning objects, so that there is
            # no need to fetch them from the cache recursively through .resolve() below
            for lobj in module_lobjs:
                precreated.get_or_create_proxy(ExerciseEntry, lobj.id, user_id, modifiers=self._modifiers)

            precreated.resolve(self.children, prefetched_data=prefetched_data)

        must_confirm = any(entry.confirm_the_level for entry in self.children)

        self._true_children_unconfirmed = must_confirm
        self._children_unconfirmed = must_confirm

    def _generate_data(
            self,
            precreated: ProxyManager,
            prefetched_data: Optional[DBData] = None,
            ):
        lobj_id, user_id = self._params[:2]
        lobj = DBData.get_db_object(prefetched_data, LearningObject, lobj_id)
        if isinstance(lobj, BaseExercise):
            self.__class__ = SubmittableExerciseEntry
            self._generate_data(precreated, prefetched_data)
            return

        prefetched_data, lobj, _, module_lobjs, child_objs = self._prefetch_data(prefetched_data)

        self._generate_common(precreated, prefetched_data, lobj, module_lobjs, child_objs)

        self._true_passed = True
        self._passed = True
        self.submission_count = 0
        self.feedback_revealed = True
        self.max_points = 0
        self._true_points = 0
        self._points = 0
        self.invalidate_time = None
        for entry in self.children:
            if entry.confirm_the_level:
                self._true_children_unconfirmed = self._true_children_unconfirmed and not entry._true_passed
                self._children_unconfirmed = self._children_unconfirmed and not entry._passed
            else:
                self.feedback_revealed = self.feedback_revealed and entry.feedback_revealed
                self.max_points += entry.max_points
                self.submission_count += entry.submission_count
                self.invalidate_time = none_min(self.invalidate_time, entry.invalidate_time)
                self._true_passed = self._true_passed and entry._true_passed
                self._passed = self._passed and entry._passed
                if type(entry) is ExerciseEntry or (isinstance(entry, SubmittableExerciseEntry) and entry.graded):
                    self._true_points += entry._true_points
                    self._points += entry._points


class SubmittableExerciseEntry(ExerciseEntry):
    # Remove ExerciseEntry from the parents. SubmittableExerciseEntry isn't buil
    # on top of ExerciseEntry but has its fields. Inheriting directly from ExerciseEntry
    # allows isinstance(..., ExerciseEntry) to work
    PARENTS = ExerciseEntry._parents[:-1]
    KEY_PREFIX = ExerciseEntry.KEY_PREFIX
    NUM_PARAMS = ExerciseEntry.NUM_PARAMS
    INVALIDATORS = [
        # ExerciseEntry handles the general learning object invalidation. Here we invalidate for reasons
        # specific to submittable exercises.
        # These invalidate exercises with confirm_the_level = True whenever any of its sibling exercises change
        (Submission, [post_delete, post_save], with_user_ids(model_exercise_siblings_confirms_the_level)),
        (DeadlineRuleDeviation, [post_delete, post_save], with_user_ids(model_exercise_siblings_confirms_the_level)),
        (MaxSubmissionsRuleDeviation, [post_delete, post_save], with_user_ids(model_exercise_siblings_confirms_the_level)),
        (RevealRule, [post_delete, post_save], with_user_ids(model_exercise_siblings_confirms_the_level)),
        (Notification, [post_delete, post_save], with_user_ids(model_exercise_ancestors)),
        (Notification, [post_delete, post_save], with_user_ids(model_exercise_siblings_confirms_the_level)),
    ]
    submissions: List[SubmissionEntry] = field(default_factory=list)
    _true_best_submission: Optional[int]
    _best_submission: Optional[int]
    graded: bool
    unofficial: bool
    confirmable_points: bool
    forced_points: bool
    notified: bool
    unseen: bool
    personal_deadline: Optional[datetime.datetime]
    personal_deadline_has_penalty: Optional[bool]
    personal_max_submissions: Optional[int]
    feedback_reveal_time: Optional[datetime.datetime]

    best_submission = RevealableAttribute[Optional[int]]()

    def post_build(self, precreated: ProxyManager):
        super().post_build(precreated)

        for submission in self.submissions:
            submission.reveal(self._modifiers[0])

    def _generate_data(
            self,
            precreated: ProxyManager,
            prefetched_data: Optional[DBData] = None,
            ):
        lobj_id, user_id = self._params[:2]
        prefetched_data, lobj, user, module_lobjs, child_lobjs = self._prefetch_data(prefetched_data)
        if not isinstance(lobj, BaseExercise):
            self.__class__ = ExerciseEntry
            self._generate_data(precreated, prefetched_data)
            return

        self._generate_common(precreated, prefetched_data, lobj, module_lobjs, child_lobjs)

        submissions = lobj.submissions.all()
        if user is not None:
            # We rely on these only containing the max deviations for user
            deadline_deviations = DBData.filter_db_objects(prefetched_data, DeadlineRuleDeviation, exercise_id=lobj_id)
            submission_deviations = DBData.filter_db_objects(prefetched_data, MaxSubmissionsRuleDeviation, exercise_id=lobj_id)
            sibling_lobjs = DBData.filter_db_objects(prefetched_data, LearningObject, parent_id=lobj.parent_id, course_module_id=lobj.course_module_id)
        else:
            deadline_deviations = []
            submission_deviations = []
            sibling_lobjs = []

        self.confirmable_points = False
        if self.confirm_the_level:
            # Only resolve siblings with confirm_the_level=False so there are not cyclical dependencies
            siblings = [precreated.get_or_create_proxy(ExerciseEntry, lobj.id, user_id, modifiers=self._modifiers) for lobj in sibling_lobjs if not lobj.category.confirm_the_level]
            if any(not s._resolved for s in siblings):
                precreated.resolve(siblings, prefetched_data=prefetched_data)

            for sibling in siblings:
                if sibling.submission_count > 0:
                    self.confirmable_points = True
                    break

        self.personal_deadline = None
        self.personal_deadline_has_penalty = None
        for deviation in deadline_deviations:
            self.personal_deadline = (
                self.closing_time + datetime.timedelta(minutes=deviation.extra_minutes)
            )
            self.personal_deadline_has_penalty = not deviation.without_late_penalty

        self.personal_max_submissions = None
        for deviation in submission_deviations:
            self.personal_max_submissions = (
                self.max_submissions + deviation.extra_submissions
            )

        self.submission_count = 0
        self._true_passed = False
        self._passed = False
        self._true_points = 0
        self.submittable = True
        self.submissions = []
        self._true_best_submission = None
        self._best_submission = None
        self.graded = False
        self.unofficial = False # TODO: this should be True,
        # but we need to ensure nothing breaks when it's changed
        self.forced_points = False
        self.notified = False
        self.unseen = False
        self.model_answer_modules = []

        # Augment submission data.
        final_submission = None
        last_submission = None

        if lobj.grading_mode == BaseExercise.GRADING_MODE.BEST:
            is_better_than = has_more_points
        elif lobj.grading_mode == BaseExercise.GRADING_MODE.LAST:
            is_better_than = is_newer
        else:
            is_better_than = has_more_points

        for submission in submissions:
            ready = submission.status == Submission.STATUS.READY
            unofficial = submission.status == Submission.STATUS.UNOFFICIAL
            if ready or submission.status in (Submission.STATUS.WAITING, Submission.STATUS.INITIALIZED):
                self.submission_count += 1
            self.submissions.append(
                SubmissionEntry(
                    id = submission.id,
                    max_points = self.max_points,
                    points_to_pass = self.points_to_pass,
                    confirm_the_level = self.confirm_the_level,
                    submission_count = 1, # to fool points badge
                    _true_passed = submission.grade >= lobj.points_to_pass,
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
                self._true_best_submission = submission.id
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
                    self._true_best_submission = submission.id
                    self._true_passed = ready and submission.grade >= self.points_to_pass
                    self._true_points = submission.grade
                    self.graded = ready # != unofficial
                    self.unofficial = unofficial

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
                self.notified = True
                if submission.notifications.filter(seen=False).exists():
                    self.unseen = True

        # These need to be set here to make sure that ExerciseRevealState below works correctly
        self._best_submission = self._true_best_submission
        self._points = self._true_points
        self._passed = self._true_passed

        if self.submissions:
            # Check the reveal rule now that all submissions for the exercise have been iterated.
            reveal_rule = lobj.active_submission_feedback_reveal_rule
            state = ExerciseRevealState(self)
            is_revealed = reveal_rule.is_revealed(state)
            reveal_time = reveal_rule.get_reveal_time(state)
        else:
            # Do not hide points if no submissions have been made
            is_revealed = True
            reveal_time = None

        timestamp = reveal_time and reveal_time.timestamp()

        if not is_revealed:
            self._best_submission = last_submission and last_submission.id
            self._points = 0
            self._passed = False

        self.feedback_revealed = is_revealed
        self.feedback_reveal_time = reveal_time
        self.invalidate_time = timestamp

        for submission in self.submissions:
            if is_revealed:
                submission._points = submission._true_points
                self._passed = self._true_passed
            else:
                submission._points = 0
                self._passed = False
            submission.feedback_revealed = is_revealed
            submission.feedback_reveal_time = reveal_time


EitherExerciseEntry = Union[ExerciseEntry, SubmittableExerciseEntry]


ModuleEntryType = TypeVar("ModuleEntryType", bound=ModuleEntryBase)
class ModuleEntry(DifficultyStats, ModuleEntryBase[ExerciseEntry]):
    KEY_PREFIX = "modulepoints"
    NUM_PARAMS = 2
    INVALIDATORS = [
        (Submission, [post_delete, post_save], with_user_ids(model_exercise_module_id)),
        (DeadlineRuleDeviation, [post_delete, post_save], with_user_ids(model_exercise_module_id)),
        (MaxSubmissionsRuleDeviation, [post_delete, post_save], with_user_ids(model_exercise_module_id)),
        (RevealRule, [post_delete, post_save], with_user_ids(model_exercise_module_id)),
        (RevealRule, [post_delete, post_save], with_user_ids(model_module_id)),
        (Submission.submitters.through, [m2m_changed], m2m_submission_userprofile(model_exercise_module_id)),
    ]
    _true_children_unconfirmed: bool
    _children_unconfirmed: bool
    invalidate_time: Optional[float]
    is_model_answer_revealed: bool

    children_unconfirmed = RevealableAttribute[bool]()

    def post_build(self, precreated: ProxyManager):
        self.reveal(self._modifiers[0])

        children = self.children
        if children and not isinstance(children[0], tuple):
            return

        user_id = self._params[1]
        modifiers = self._modifiers
        for i, params in enumerate(children):
            children[i] = precreated.get_or_create_proxy(ExerciseEntry, *params[0], user_id, modifiers=modifiers)

    def is_valid(self) -> bool:
        return (
            self.invalidate_time is None
            or time() >= self.invalidate_time
        )

    def _generate_data(
            self,
            precreated: ProxyManager,
            prefetched_data: Optional[DBData] = None,
            ):
        module_id, user_id = self._params[:2]
        if not prefetched_data:
            prefetched_data = DBData()

            if user_id is not None:
                user = User.objects.get(id=user_id)
            else:
                user = None

            module = CourseModule.objects.get(id=module_id)
            lobjs = module.learning_objects.all()

            prefetched_data.add(module)
            prefetched_data.extend(LearningObject, lobjs)

            prefetch_exercise_data(prefetched_data, user, lobjs)
        else:
            module = prefetched_data.get_db_object(CourseModule, module_id)
            lobjs = prefetched_data.filter_db_objects(LearningObject, course_module_id=module_id)

        exercises = [precreated.get_or_create_proxy(ExerciseEntry, lobj.id, user_id, modifiers=self._modifiers) for lobj in lobjs]
        if any(not s._resolved for s in exercises):
            precreated.resolve(exercises, prefetched_data=prefetched_data)

        self.submissions = 0
        self.submission_count = 0
        self._true_passed = True
        self._passed = True
        self._true_points = 0
        self._points = 0
        self.feedback_revealed = True
        self.invalidate_time = None
        self._true_points_by_difficulty = {}
        self._points_by_difficulty = {}
        self._true_unconfirmed_points_by_difficulty = {}
        self._unconfirmed_points_by_difficulty = {}

        self.children = [ex for ex in exercises if ex.parent is None]

        must_confirm = any(entry.confirm_the_level for entry in self.children)
        self._true_children_unconfirmed = must_confirm
        self._children_unconfirmed = must_confirm
        for entry in self.children:
            if entry.confirm_the_level:
                self._true_children_unconfirmed = self._true_children_unconfirmed and not entry._true_passed
                self._children_unconfirmed = self._children_unconfirmed and not entry._passed

        for entry in exercises:
            if not entry.confirm_the_level and isinstance(entry, SubmittableExerciseEntry):
                self.invalidate_time = none_min(self.invalidate_time, entry.invalidate_time)
                _add_to(self, entry)

        self._true_passed = self._true_passed and self._true_points >= self.points_to_pass
        self._passed = self._passed and self._points >= self.points_to_pass

        self.is_model_answer_revealed = True
        model_chapter = module.model_answer
        if model_chapter is not None:
            reveal_rule = module.active_model_solution_reveal_rule
            state = ModuleRevealState(self)
            self.is_model_answer_revealed = reveal_rule.is_revealed(state)
            reveal_time = reveal_rule.get_reveal_time(state)
            timestamp = reveal_time and reveal_time.timestamp()
            self.invalidate_time = none_min(self.invalidate_time, timestamp)


CachedPointsDataType = TypeVar("CachedPointsDataType", bound="CachedPointsData")
class CachedPointsData(CachedDataBase[ModuleEntry, EitherExerciseEntry, CategoryEntry, Totals]):
    KEY_PREFIX: ClassVar[str] = 'instancepoints'
    NUM_PARAMS: ClassVar[int] = 2
    INVALIDATORS = [
        (Submission, [post_delete, post_save], with_user_ids(model_instance_id)),
        (DeadlineRuleDeviation, [post_delete, post_save], with_user_ids(model_instance_id)),
        (MaxSubmissionsRuleDeviation, [post_delete, post_save], with_user_ids(model_instance_id)),
        (RevealRule, [post_delete, post_save], with_user_ids(model_instance_id)),
        # listen to the m2m_changed signal since submission.submitters is a many-to-many
        # field and instances must be saved before the many-to-many fields may be modified,
        # that is to say, the submission post save hook may see an empty submitters list
        (Submission.submitters.through, [m2m_changed], m2m_submission_userprofile(model_instance_id)),
    ]
    user_id: InitVar[int]
    invalidate_time: Optional[float]
    points_created: datetime.datetime
    categories: Dict[int, CategoryEntry]
    total: Totals

    def post_build(self, precreated: ProxyManager):
        show_unrevealed = self._modifiers[0]
        self.total.reveal(show_unrevealed)
        for category in self.categories.values():
            category.reveal(show_unrevealed)

        if self.modules and not isinstance(self.modules[0], tuple):
            return

        user_id = self._params[1]
        modifiers = self._modifiers

        modules = self.modules
        module_index = self.module_index
        for i, module_params in enumerate(modules):
            proxy = precreated.get_or_create_proxy(ModuleEntry, *module_params[0], user_id, modifiers=modifiers)
            modules[i] = proxy
            module_index[module_params[0][0]] = proxy

        exercise_index = self.exercise_index
        for k, exercise_params in exercise_index.items():
            exercise_index[k] = precreated.get_or_create_proxy(ExerciseEntry, *exercise_params[0], user_id, modifiers=modifiers)

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

    def is_valid(self) -> bool:
        return (
            self.points_created >= self.created
            and (
                self.invalidate_time is None
                or time() < self.invalidate_time
            )
        )

    def _generate_data(
            self,
            precreated: ProxyManager,
            prefetched_data: Optional[DBData] = None,
            ):
        instance_id, user_id = self._params
        if not prefetched_data:
            prefetched_data = DBData()

            modules = CourseModule.objects.filter(course_instance_id=instance_id)
            lobjs = LearningObject.objects.filter(course_module__in=modules)

            prefetched_data.extend(CourseModule, modules)
            prefetched_data.extend(LearningObject, lobjs)

            if user_id is not None:
                user = User.objects.get(id=user_id)
            else:
                user = None

            prefetch_exercise_data(prefetched_data, user, lobjs)

        for category in self.categories.values():
            CategoryEntry.upgrade(category)
        Totals.upgrade(self.total)

        self.exercise_index = {
            id: precreated.get_or_create_proxy(ExerciseEntry, id, user_id, modifiers=self._modifiers)
            for id in self.exercise_index
        }
        if self.modules and isinstance(self.modules[0], tuple):
            self.modules = [
                precreated.get_or_create_proxy(ModuleEntry, module[0][0], user_id, modifiers=self._modifiers)
                for module in self.modules
            ]
        else:
            self.modules = [
                precreated.get_or_create_proxy(ModuleEntry, *module._params, user_id, modifiers=self._modifiers)
                for module in self.modules
            ]

        self.module_index = {
            module._params[0]: module
            for module in self.modules
        }

        precreated.resolve(self.get_child_proxies(), prefetched_data=prefetched_data)

        self.total.reset_points()
        for category in self.categories.values():
            category.reset_points()

        self.invalidate_time = None
        for entry in self.exercise_index.values():
            if not entry.confirm_the_level and isinstance(entry, SubmittableExerciseEntry):
                self.invalidate_time = none_min(self.invalidate_time, entry.invalidate_time)
                _add_to(self.categories[entry.category_id], entry)
                _add_to(self.total, entry)

        for category in self.categories.values():
            category._true_passed = category._true_points >= category.points_to_pass
            category._passed = category._points >= category.points_to_pass

        self.points_created = timezone.now()


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
    def invalidate(cls, instance: CourseInstance, user: User):
        CachedPointsData.invalidate(instance, user)
        for module in instance.course_modules.prefetch_related("learning_objects").all():
            ModuleEntryBase.invalidate(module, user)
            for exercise in module.learning_objects.all():
                ExerciseEntryBase.invalidate(exercise, user)


# Required so that Submission post_delete receivers can access submitters
def prefetch_submitters(sender: Type[Submission], instance: Submission, **kwargs: Any) -> None:
    prefetch_related_objects([instance], "submitters")


# Required so that RevealRule post_delete receivers can access exercise
def prefetch_exercise(sender: Type[RevealRule], instance: RevealRule, **kwargs: Any) -> None:
    try:
        instance.exercise = BaseExercise.objects.get(submission_feedback_reveal_rule=instance)
    except BaseExercise.DoesNotExist:
        instance.exercise = None


# Required so that RevealRule post_delete receivers can access module
def prefetch_module(sender: Type[RevealRule], instance: RevealRule, **kwargs: Any) -> None:
    try:
        instance.module = CourseModule.objects.get(model_solution_reveal_rule=instance)
    except CourseModule.DoesNotExist:
        instance.module = None


pre_delete.connect(prefetch_submitters, Submission)
pre_delete.connect(prefetch_exercise, RevealRule)
pre_delete.connect(prefetch_module, RevealRule)
