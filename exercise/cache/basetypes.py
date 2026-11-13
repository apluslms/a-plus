from __future__ import annotations
from dataclasses import dataclass, field, InitVar
from datetime import datetime
from typing import Any, ClassVar, Dict, Generic, Iterable, List, Literal, Optional, Set, Tuple, Type, TypeVar, Union

from django.db.models import Prefetch, QuerySet
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_delete, pre_save
from django.utils import timezone

from course.models import CourseInstance, CourseInstanceProto, CourseModule, CourseModuleProto
from lib.cache.cached import CacheBase, DBDataManager, Dependencies, ProxyManager
from threshold.models import (
    are_threshold_points_passed,
    CourseModuleRequirement,
    format_requirement_description,
    Threshold,
    ThresholdPoints,
)
from .invalidate_util import (
    capture_previous_numbering,
    capture_previous_requirement_module,
    capture_previous_threshold_point_owner,
    category_learning_objects,
    module_learning_objects,
    requirement_modules,
    saved_threshold_point_modules,
    threshold_m2m_modules,
    threshold_modules,
    threshold_modules_for_learning_object,
    threshold_modules_for_numbering,
    threshold_modules_for_target,
    threshold_point_modules,
)
from ..models import BaseExercise, CourseChapter, LearningObject, LearningObjectCategory, LearningObjectProto


def add_by_difficulty(to: Dict[str, int], difficulty: str, points: int):
    if difficulty in to:
        to[difficulty] += points
    else:
        to[difficulty] = points


def _add_to(target: Union[ModuleEntryBase, CategoryEntryBase, TotalsBase], exercise: BaseExercise) -> None:
    target.exercise_count += 1
    target.max_points += exercise.max_points
    add_by_difficulty(
        target.max_points_by_difficulty,
        exercise.difficulty,
        exercise.max_points
    )


class EqById:
    """Implements equality operator by comparing the id attribute"""
    id: int

    def __eq__(self, other: Any) -> bool:
        if type(self) != type(other): # pylint: disable=unidiomatic-typecheck # noqa: E721
            return False
        return self.id == other.id


@dataclass(frozen=True)
class CachedRequirementDescription:
    passed_modules: Tuple[str, ...] = ()
    passed_categories: Tuple[str, ...] = ()
    passed_exercises: Tuple[str, ...] = ()
    points: Tuple[Tuple[str, int], ...] = ()
    negative: bool = False

    @classmethod
    def from_requirement(cls, requirement: CourseModuleRequirement) -> CachedRequirementDescription:
        threshold = requirement.threshold
        return cls(
            passed_modules=tuple(str(m) for m in threshold.passed_modules.all()),
            passed_categories=tuple(str(c) for c in threshold.passed_categories.all()),
            passed_exercises=tuple(str(e) for e in threshold.passed_exercises.all()),
            points=tuple((p.difficulty, p.limit) for p in threshold.points.all()),
            negative=requirement.negative,
        )

    def format(self) -> str:
        return format_requirement_description(
            self.passed_modules,
            self.passed_categories,
            self.passed_exercises,
            self.points,
            negative=self.negative,
        )

    def __str__(self) -> str:
        return self.format()


@dataclass(frozen=True)
class CachedRequirementRule:
    passed_module_ids: Tuple[int, ...] = ()
    passed_category_ids: Tuple[int, ...] = ()
    passed_exercise_ids: Tuple[int, ...] = ()
    points: Tuple[Tuple[str, int], ...] = ()
    consume_harder_points: bool = False
    negative: bool = False

    @classmethod
    def from_requirement(cls, requirement: CourseModuleRequirement) -> CachedRequirementRule:
        threshold = requirement.threshold
        return cls(
            passed_module_ids=tuple(m.id for m in threshold.passed_modules.all()),
            passed_category_ids=tuple(c.id for c in threshold.passed_categories.all()),
            passed_exercise_ids=tuple(e.id for e in threshold.passed_exercises.all()),
            points=tuple((p.difficulty, p.limit) for p in threshold.points.all()),
            consume_harder_points=threshold.consume_harder_points,
            negative=requirement.negative,
        )

    def _is_threshold_passed(self, data: Any) -> bool:
        for module_id in self.passed_module_ids:
            module_entry = data.module_index.get(module_id)
            if module_entry is None or not module_entry.passed:
                return False
        for category_id in self.passed_category_ids:
            category_entry = data.categories.get(category_id)
            if category_entry is None or not category_entry.passed:
                return False
        for exercise_id in self.passed_exercise_ids:
            exercise_entry = data.exercise_index.get(exercise_id)
            if exercise_entry is None or not exercise_entry.passed:
                return False

        total = data.total
        d_points = total.points_by_difficulty.copy()
        for key, value in total.unconfirmed_points_by_difficulty.items():
            if key in d_points:
                d_points[key] += value
            else:
                d_points[key] = value
        return are_threshold_points_passed(
            self.points,
            self.consume_harder_points,
            total.points,
            d_points,
        )

    def is_passed(self, data: Any) -> bool:
        passed = self._is_threshold_passed(data)
        return not passed if self.negative else passed


LearningObjectEntry = TypeVar("LearningObjectEntry", bound="LearningObjectEntryBase")
ModuleEntry = TypeVar("ModuleEntry", bound="ModuleEntryBase")
CategoryEntry = TypeVar("CategoryEntry", bound="CategoryEntryBase")
Totals = TypeVar("Totals", bound="TotalsBase")


class ContentDBData(DBDataManager):
    exercises: Dict[int, LearningObject]
    needed_exercises: Set[int]
    modules: Dict[int, CourseModule]
    needed_modules: Set[int]
    instances: Dict[int, CourseInstance]
    needed_instances: Set[int]
    exercise_children: Dict[int, List[LearningObject]]
    module_children: Dict[int, List[LearningObject]]
    module_exercises: Dict[int, List[LearningObject]]
    instance_modules: Dict[int, List[CourseModule]]
    instance_exercises: Dict[int, List[LearningObject]]

    def __init__(self):
        self.exercises = {}
        self.needed_exercises = set()
        self.modules = {}
        self.needed_modules = set()
        self.instances = {}
        self.needed_instances = set()
        self.exercise_children = {}
        self.module_children = {}
        self.module_exercises = {}
        self.instance_modules = {}
        self.instance_exercises = {}

    def add(self, proxy: Union[CachedDataBase, ModuleEntryBase, LearningObjectEntryBase]) -> None:
        model_id = proxy._params[0]
        if isinstance(proxy, CachedDataBase) and model_id not in self.instances:
            self.needed_instances.add(model_id)
        elif isinstance(proxy, ModuleEntryBase) and model_id not in self.modules:
            self.needed_modules.add(model_id)
        elif isinstance(proxy, LearningObjectEntryBase) and model_id not in self.exercises:
            self.needed_exercises.add(model_id)

    def _load_modules_qs(self, module_qs: QuerySet[CourseModule]) -> Iterable[CourseModule]:
        new_modules = module_qs.exclude(id__in=self.modules).prefetch_related(
            Prefetch(
                "requirements",
                queryset=(
                    CourseModuleRequirement.objects
                    .select_related("threshold")
                    .prefetch_related(
                        Prefetch(
                            "threshold__passed_modules",
                            queryset=CourseModule.objects.only(
                                "id",
                                "order",
                                "name",
                                "course_instance__module_numbering",
                                "course_instance__course_id",
                            ),
                        ),
                        Prefetch(
                            "threshold__passed_categories",
                            queryset=LearningObjectCategory.objects.only("id", "name"),
                        ),
                        Prefetch(
                            "threshold__passed_exercises",
                            queryset=BaseExercise.bare_objects.select_related(
                                "course_module__course_instance",
                                "parent",
                            ).only(
                                "id",
                                "order",
                                "name",
                                "parent_id",
                                "course_module_id",
                                "course_module__order",
                                "course_module__course_instance__content_numbering",
                                "course_module__course_instance__module_numbering",
                                "parent__id",
                                "parent__order",
                                "parent__parent_id",
                            ),
                        ),
                        "threshold__points",
                    )
                )
            ),
        )
        self.modules.update(
            (module.id, module)
            for module in new_modules
        )

        affected_instances = set()
        for module in new_modules:
            self.instance_modules.setdefault(module.course_instance_id, []).append(module)
            affected_instances.add(module.course_instance_id)

        for instance_id in affected_instances:
            self.instance_modules[instance_id].sort(
                key=lambda module: (module.order, module.closing_time, module.id)
            )

        new_exercises = LearningObject.objects.filter(course_module__in=new_modules).select_related("category")
        self.exercises.update(
            (exercise.id, exercise)
            for exercise in new_exercises
        )

        self.needed_exercises.difference_update(e.id for e in new_exercises)

        for exercise in new_exercises:
            if exercise.parent_id is not None:
                self.exercise_children.setdefault(exercise.parent_id, []).append(exercise)

        for exercise in new_exercises:
            if exercise.course_module_id is not None:
                self.module_exercises.setdefault(exercise.course_module_id, []).append(exercise)
                if exercise.parent_id is None:
                    self.module_children.setdefault(exercise.course_module_id, []).append(exercise)

        return new_modules

    def _load_modules(self, module_ids: Iterable[int]) -> Iterable[CourseModule]:
        return self._load_modules_qs(CourseModule.objects.filter(id__in=module_ids))

    def fetch(self) -> None:
        if self.needed_instances:
            new_instances = CourseInstance.objects.filter(id__in=self.needed_instances)
            self.instances.update(
                (instance.id, instance)
                for instance in new_instances
            )

            new_modules = self._load_modules_qs(CourseModule.objects.filter(course_instance__in=new_instances))
            self.needed_modules.difference_update(m.id for m in new_modules)
            self.needed_instances.clear()

        if self.needed_modules:
            self._load_modules(self.needed_modules)
            self.needed_modules.clear()

        if self.needed_exercises:
            new_exercises = LearningObject.objects.filter(id__in=self.needed_exercises).select_related("category")
            # This also sets the exercises we just loaded in self.exercises
            self._load_modules(e.course_module_id for e in new_exercises if e.course_module_id not in self.modules)
            self.needed_exercises.clear()

    def get_instance(self, instance_id: int) -> CourseInstance:
        if instance_id in self.instances:
            return self.instances[instance_id]
        raise CourseInstance.DoesNotExist()

    def get_module(self, module_id: int) -> CourseModule:
        if module_id in self.modules:
            return self.modules[module_id]
        raise CourseModule.DoesNotExist()

    def get_exercise(self, exercise_id: int) -> LearningObject:
        if exercise_id in self.exercises:
            return self.exercises[exercise_id]
        raise LearningObject.DoesNotExist()

    def get_exercise_children(self, parent_id: int) -> List[LearningObject]:
        return self.exercise_children.get(parent_id, [])

    def get_module_children(self, module_id: int) -> List[LearningObject]:
        return self.module_children.get(module_id, [])

    def get_module_exercises(self, module_id: int) -> List[LearningObject]:
        return self.module_exercises.get(module_id, [])

    def get_instance_modules(self, instance_id: int) -> List[CourseModule]:
        return self.instance_modules.get(instance_id, [])

    def get_instance_exercises(self, instance_id: int) -> List[LearningObject]:
        modules = self.instance_modules.get(instance_id, [])
        return [
            exercise
            for module in modules
            for exercise in self.get_module_exercises(module.id)
        ]


class LearningObjectEntryBase(LearningObjectProto, CacheBase, EqById, Generic[ModuleEntry, LearningObjectEntry]):
    PROTO_BASES = (LearningObjectProto,)
    DBCLS = ContentDBData
    KEY_PREFIX: ClassVar[str] = 'exercise'
    NUM_PARAMS: ClassVar[int] = 1
    INVALIDATORS = [
        (LearningObject, [post_delete, post_save], ("id",)),
        (LearningObject, [post_delete, post_save], ("parent_id",)), # In case the parent changed
        (LearningObjectCategory, [post_delete, post_save], category_learning_objects(lambda lobj: [lobj.id])),
        (CourseModule, [post_delete, post_save], module_learning_objects),
    ]
    type: ClassVar[Literal['exercise']] = 'exercise'
    # Disable repr for ancestors so there are no infinite loops
    module: ModuleEntry
    parent: Optional[LearningObjectEntry]
    category: str
    category_id: int
    category_status: str
    confirm_the_level: bool
    module_id: int
    module_status: str
    id: int
    url: str
    order: int
    status: str
    name: str
    hierarchical_name: str
    number: str
    link: str
    submissions_link: str
    requirement_descriptions: List[CachedRequirementDescription]
    opening_time: datetime
    reading_opening_time: Optional[datetime]
    closing_time: datetime
    late_allowed: bool
    late_time: datetime
    late_percent: int
    is_empty: bool
    points_to_pass: int
    difficulty: str
    max_submissions: int
    max_points: int
    allow_assistant_viewing: bool
    children: List[LearningObjectEntry]
    submittable: bool
    grading_mode: Optional[int]
    model_answer_modules: List[ModuleEntry]
    has_submittable_files: bool

    @property
    def course_module(self):
        return self.module

    @property
    def requirements(self) -> List[str]:
        if self.module._resolved:
            return self.module.requirements
        return [description.format() for description in self.requirement_descriptions]

    def parent_list(self):
        if self.parent is None:
            return [self]
        return self.parent.parent_list() + [self]

    def __str__(self) -> str:
        return self.name

    def get_child_proxies(self) -> List[CacheBase]:
        children = [self.module, *self.children]
        if self.parent is not None:
            children.append(self.parent)
        return children

    def _generate_data(
            self,
            precreated: ProxyManager,
            prefetched_data: LearningObjectEntryBase.DBCLS,
            ) -> Optional[Dependencies]:
        """ Returns object that is cached into self.data """
        lobj_id = self._params[0]
        lobj = prefetched_data.get_exercise(lobj_id)
        module = prefetched_data.get_module(lobj.course_module_id)
        children = prefetched_data.get_exercise_children(lobj_id)

        category = lobj.category

        exercise_info = lobj.exercise_info
        has_submittable_files = (
            bool(exercise_info)
            and exercise_info.get('form_spec')
            and isinstance(exercise_info['form_spec'], list)
            and any(map(lambda item: item.get('type') == 'file', exercise_info['form_spec']))
        )

        self.module = precreated.get_or_create_proxy(ModuleEntryBase, module.id)
        if lobj.parent_id is None:
            self.parent = None
        else:
            self.parent = precreated.get_or_create_proxy(LearningObjectEntryBase, lobj.parent_id)
        self.has_submittable_files = has_submittable_files
        self.category = str(category)
        self.category_id = category.id
        self.category_status = category.status
        self.confirm_the_level = category.confirm_the_level
        self.module_id = module.id
        self.module_status = module.status
        self.id = lobj.id
        self.url = lobj.url
        self.order = lobj.order
        self.status = lobj.status
        self.name = str(lobj)
        self.hierarchical_name = lobj.hierarchical_name()
        self.number = str(module.order) + '.' + lobj.number()
        self.link = lobj.get_display_url()
        self.submissions_link = lobj.get_submission_list_url()
        self.requirement_descriptions = [
            CachedRequirementDescription.from_requirement(r)
            for r in module.requirements.all()
        ]
        self.opening_time = module.opening_time
        self.reading_opening_time = module.reading_opening_time
        self.closing_time = module.closing_time
        self.late_allowed = module.late_submissions_allowed
        self.late_time = module.late_submission_deadline
        self.late_percent = module.get_late_submission_point_worth()
        self.is_empty = lobj.is_empty()
        self.children = [precreated.get_or_create_proxy(LearningObjectEntryBase, o.id) for o in children]
        if isinstance(lobj, CourseChapter):
            self.model_answer_modules = [
                precreated.get_or_create_proxy(ModuleEntryBase, module.id)
                for module in lobj.model_answer_modules.all()
            ]
        else:
            self.model_answer_modules = []


        if isinstance(lobj, BaseExercise):
            self.submittable = True
            self.points_to_pass = lobj.points_to_pass
            self.difficulty = lobj.difficulty
            self.max_submissions = lobj.max_submissions
            self.max_points = lobj.max_points
            self.allow_assistant_viewing = lobj.allow_assistant_viewing
            self.grading_mode = lobj.grading_mode
        else:
            self.submittable = False
            self.points_to_pass = 0
            self.difficulty = ''
            self.max_submissions = 0
            self.max_points = 0
            self.allow_assistant_viewing = False
            self.grading_mode = None

        # This is required so that dependency detection doesn't trigger
        # when loaded the next time.
        precreated.resolve(self.children)

        # We cannot rely on INVALIDATORS as the parent of a child might change,
        # in which case this object wouldn't be invalidated (and the children would be wrong)
        return {LearningObjectEntryBase: [proxy._params for proxy in self.children]}


class ModuleEntryBase(CourseModuleProto, CacheBase, EqById, Generic[LearningObjectEntry]):
    PROTO_BASES = (CourseModuleProto,)
    DBCLS = ContentDBData
    KEY_PREFIX: ClassVar[str] = 'module'
    NUM_PARAMS: ClassVar[int] = 1
    INVALIDATORS = [
        (CourseModule, [post_delete, post_save], ("id",)),
        (CourseModule, [pre_delete, post_save], threshold_modules_for_target),
        (CourseInstance, [post_save], threshold_modules_for_numbering),
        (LearningObject, [post_delete, post_save], ("course_module_id",)),
        # Exercise saves reach LearningObject receivers through LearningObject.save(); BaseExercise misses subclasses
        (LearningObject, [post_delete, post_save], threshold_modules_for_learning_object),
        (
            LearningObjectCategory,
            [post_delete, post_save],
            category_learning_objects(lambda lobj: [lobj.course_module_id]),
        ),
        (LearningObjectCategory, [pre_delete, post_save], threshold_modules_for_target),
        (BaseExercise, [pre_delete], threshold_modules_for_target),
        (CourseModuleRequirement, [post_delete], ("module_id",)),
        (CourseModuleRequirement, [post_save], requirement_modules),
        (Threshold, [pre_delete, post_save], threshold_modules),
        (ThresholdPoints, [post_delete], threshold_point_modules),
        (ThresholdPoints, [post_save], saved_threshold_point_modules),
        (
            Threshold.passed_modules.through,
            [m2m_changed],
            (threshold_m2m_modules, ("action", "pk_set", "reverse")),
        ),
        (
            Threshold.passed_categories.through,
            [m2m_changed],
            (threshold_m2m_modules, ("action", "pk_set", "reverse")),
        ),
        (
            Threshold.passed_exercises.through,
            [m2m_changed],
            (threshold_m2m_modules, ("action", "pk_set", "reverse")),
        ),
    ]
    type: ClassVar[Literal['module']] = 'module'
    id: int
    order: int
    status: str
    url: str
    name: str
    number: str
    introduction: str
    link: str
    requirement_descriptions: List[CachedRequirementDescription]
    requirement_rules: List[CachedRequirementRule]
    opening_time: datetime
    reading_opening_time: Optional[datetime]
    closing_time: datetime
    late_allowed: bool
    late_time: datetime
    late_percent: int
    points_to_pass: int
    exercise_count: int
    max_points: int
    max_points_by_difficulty: Dict[str, int]
    instance: "CachedDataBase"
    children: List[LearningObjectEntry]

    @property
    def course_instance(self) -> "CachedDataBase":
        return self.instance

    @property
    def requirements(self) -> List[str]:
        return [description.format() for description in self.requirement_descriptions]

    def is_visible(self) -> bool:
        return self.status != CourseModule.STATUS.HIDDEN

    def is_listed(self) -> bool:
        return self.is_visible() and self.status != CourseModule.STATUS.UNLISTED

    def is_in_maintenance(self) -> bool:
        return self.status == CourseModule.STATUS.MAINTENANCE

    def get_child_proxies(self) -> Iterable[CacheBase]:
        return self.children

    def _generate_data(
            self,
            precreated: ProxyManager,
            prefetched_data: ModuleEntryBase.DBCLS,
            ) -> Optional[Dependencies]:
        """ Returns object that is cached into self.data """
        module_id = self._params[0]
        module = prefetched_data.get_module(module_id)
        lobjs = prefetched_data.get_module_exercises(module_id)
        children = prefetched_data.get_module_children(module_id)

        self.id = module.id
        self.order = module.order
        self.status = module.status
        self.url = module.url
        self.name = str(module)
        self.number = str(module.order)
        self.introduction = module.introduction
        self.link = module.get_absolute_url()
        requirements = list(module.requirements.all())
        self.requirement_rules = [CachedRequirementRule.from_requirement(r) for r in requirements]
        self.requirement_descriptions = [CachedRequirementDescription.from_requirement(r) for r in requirements]
        self.opening_time = module.opening_time
        self.reading_opening_time = module.reading_opening_time
        self.closing_time = module.closing_time
        self.late_allowed = module.late_submissions_allowed
        self.late_time = module.late_submission_deadline
        self.late_percent = module.get_late_submission_point_worth()
        self.points_to_pass = module.points_to_pass
        self.instance = precreated.get_or_create_proxy(CachedDataBase, module.course_instance_id)
        self.children = [precreated.get_or_create_proxy(LearningObjectEntryBase, child.id) for child in children]
        self.exercise_count = 0
        self.max_points = 0
        self.max_points_by_difficulty = {}

        for exercise in lobjs:
            if isinstance(exercise, BaseExercise):
                if not exercise.category.confirm_the_level and exercise.is_visible():
                    _add_to(self, exercise)

        # We rely on the module of an exercise never changing, so the invalidators do the work
        # without the need for dependencies
        return {}


@dataclass(eq=False)
class CategoryEntryBase(EqById):
    type: ClassVar[Literal['category']] = 'category'
    id: int
    status: str
    name: str
    points_to_pass: int
    exercise_count: int = 0
    max_points: int = 0
    max_points_by_difficulty: Dict[str, int] = field(default_factory=dict)

    def is_visible(self) -> bool:
        return self.status not in (
            LearningObjectCategory.STATUS.HIDDEN,
            LearningObjectCategory.STATUS.NOTOTAL,
        )

    def is_listed(self) -> bool:
        return self.is_visible()

    def is_in_maintenance(self) -> bool:
        return False


@dataclass
class TotalsBase:
    exercise_count: int = 0
    max_points: int = 0
    max_points_by_difficulty: Dict[str, int] = field(default_factory=dict)
    min_group_size: int = 100000
    max_group_size: int = 1


CachedDataBaseType = TypeVar("CachedDataBaseType", bound="CachedDataBase")
class CachedDataBase(CourseInstanceProto, CacheBase, Generic[ModuleEntry, LearningObjectEntry, CategoryEntry, Totals]):
    PROTO_BASES = (CourseInstanceProto,)
    DBCLS = ContentDBData
    KEY_PREFIX: ClassVar[str] = 'instance'
    NUM_PARAMS: ClassVar[int] = 1
    INVALIDATORS = [
        (CourseInstance, [post_delete, post_save], ("id",)),
        (CourseModule, [post_delete, post_save], ("course_instance_id",)),
        (LearningObject, [post_delete, post_save], (["course_module", "course_instance_id"],)),
        (
            LearningObjectCategory,
            [post_delete, post_save],
            category_learning_objects(lambda lobj: [lobj.course_module.course_instance_id]),
        ),
    ]
    instance_id: InitVar[int]
    url: str
    course_url_kwargs: Dict[str, str]
    created: datetime
    module_index: Dict[int, ModuleEntry]
    exercise_index: Dict[int, LearningObjectEntry]
    paths: Dict[int, Dict[str, int]]
    modules: List[ModuleEntry]
    is_on_lifesupport: bool
    lifesupport_start: Optional[datetime]
    categories: Dict[int, CategoryEntry]
    total: Totals

    def get_course_url_kwargs(self):
        return self.course_url_kwargs

    @classmethod
    def get( # pylint: disable=arguments-differ
            cls: Type[CachedDataBaseType],
            instance: Union[CourseInstance, int],
            prefetch_children: bool = True,
            ) -> CachedDataBaseType:
        return super()._get(
            params=cls.parameter_ids(instance),
            prefetch_children=prefetch_children,
        )

    def get_child_proxies(self) -> Iterable[CacheBase]:
        return self.modules + list(self.exercise_index.values())

    def _generate_data( # pylint: disable=too-many-locals
            self,
            precreated: ProxyManager,
            prefetched_data: CachedDataBase.DBCLS,
            ) -> Optional[Dependencies]:
        """ Returns object that is cached into self.data """
        instance_id = self._params[0]
        instance = prefetched_data.get_instance(instance_id)
        module_objs = prefetched_data.get_instance_modules(instance_id)
        lobjs = prefetched_data.get_instance_exercises(instance_id)

        self.url = instance.url
        self.course_url_kwargs = instance.course.get_url_kwargs()
        self.is_on_lifesupport = instance.is_on_lifesupport()
        self.lifesupport_start = instance.lifesupport_start

        self.exercise_index = exercise_index = {}
        self.module_index = module_index = {}
        self.paths = paths = {}
        self.modules = modules = []
        self.categories = categories = {}
        self.total = total = TotalsBase()

        for lobj in lobjs:
            exercise_index[lobj.id] = precreated.get_or_create_proxy(LearningObjectEntryBase, lobj.id)
            category = lobj.category
            if category.id not in categories:
                categories[category.id] = CategoryEntryBase(
                    id = category.id,
                    status = category.status,
                    name = str(category),
                    points_to_pass = category.points_to_pass,
                )

        # Collect each module.
        for module in module_objs:
            entry = precreated.get_or_create_proxy(ModuleEntryBase, module.id)
            modules.append(entry)
            module_index[module.id] = entry
            paths[module.id] = {}

        precreated.resolve(self.get_child_proxies())

        for entry in exercise_index.values():
            paths[entry.module.id][entry.get_path()] = entry.id

        # Augment submittable exercise parameters.
        for exercise in lobjs:
            if isinstance(exercise, BaseExercise):
                entry = exercise_index[exercise.id]
                # TODO: should this be is_listed?
                if not entry.confirm_the_level and entry.is_visible():
                    _add_to(categories[entry.category_id], exercise)
                    _add_to(total, exercise)

                    total.max_group_size = max(total.max_group_size, exercise.max_group_size)
                    if exercise.max_group_size > 1 and exercise.min_group_size < total.min_group_size:
                        total.min_group_size = exercise.min_group_size

        if total.min_group_size > total.max_group_size:
            total.min_group_size = 1

        self.created = timezone.now()

        # We rely on the instance of a module never changing, so the invalidators do the work
        # without the need for dependencies
        return {}


pre_save.connect(capture_previous_requirement_module, sender=CourseModuleRequirement, weak=False)
pre_save.connect(capture_previous_threshold_point_owner, sender=ThresholdPoints, weak=False)
pre_save.connect(capture_previous_numbering, sender=CourseInstance, weak=False)
