from __future__ import annotations
from dataclasses import dataclass, field, InitVar
from datetime import datetime
from typing import Any, ClassVar, Dict, Generic, Iterable, List, Literal, Optional, Type, TypeVar, Union

from django.db.models import Prefetch
from django.db.models.signals import post_delete, post_save
from django.utils import timezone

from course.models import CourseInstance, CourseModule
from lib.cache.cached import CacheBase, DBData, ProxyManager
from threshold.models import CourseModuleRequirement
from .invalidate_util import category_learning_objects, learning_object_ancestors, module_learning_objects
from ..models import BaseExercise, LearningObject, LearningObjectCategory


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
        if type(self) != type(other): # pylint: disable=unidiomatic-typecheck
            return False
        return self.id == other.id


ExerciseEntry = TypeVar("ExerciseEntry", bound="ExerciseEntryBase")
ModuleEntry = TypeVar("ModuleEntry", bound="ModuleEntryBase")
CategoryEntry = TypeVar("CategoryEntry", bound="CategoryEntryBase")
Totals = TypeVar("Totals", bound="TotalsBase")


class ExerciseEntryBase(CacheBase, EqById, Generic[ModuleEntry, ExerciseEntry]):
    KEY_PREFIX: ClassVar[str] = 'exercise'
    NUM_PARAMS: ClassVar[int] = 1
    INVALIDATORS = [
        (LearningObject, [post_delete, post_save], learning_object_ancestors),
        (LearningObjectCategory, [post_delete, post_save], category_learning_objects(learning_object_ancestors)),
        (CourseModule, [post_delete, post_save], module_learning_objects),
    ]
    type: ClassVar[Literal['exercise']] = 'exercise'
    # Disable repr for ancestors so there are no infinite loops
    module: ModuleEntry
    parent: Optional[ExerciseEntry]
    category: str
    category_id: int
    category_status: str
    confirm_the_level: bool
    module_id: int
    module_status: str
    id: int
    order: int
    status: str
    name: str
    hierarchical_name: str
    number: str
    link: str
    submissions_link: str
    requirements: List[str]
    opening_time: datetime
    reading_opening_time: Optional[datetime]
    closing_time: datetime
    late_allowed: bool
    late_time: datetime
    late_percent: int
    is_empty: bool
    get_path: str
    points_to_pass: int
    difficulty: str
    max_submissions: int
    max_points: int
    allow_assistant_viewing: bool
    children: List[ExerciseEntry]
    submittable: bool

    def post_build(self, precreated: ProxyManager):
        if not isinstance(self.module, tuple):
            return

        self.module = precreated.get_or_create_proxy(ModuleEntryBase, *self.module[0])

        if self.parent:
            self.parent = precreated.get_or_create_proxy(ExerciseEntryBase, *self.parent[0])

        for i, params in enumerate(self.children):
            self.children[i] = precreated.get_or_create_proxy(ExerciseEntryBase, *params[0])

    def get_proxy_keys(self) -> Iterable[str]:
        return ["module", "parent", "children"]

    def get_child_proxies(self) -> List[CacheBase]:
        children = [self.module, *self.children]
        if self.parent is not None:
            children.append(self.parent)
        return children

    # pylint: disable-next=arguments-differ too-many-locals
    def _generate_data(
            self,
            precreated: ProxyManager,
            prefetched_data: Optional[DBData] = None,
            ):
        """ Returns object that is cached into self.data """
        lobj_id = self._params[0]
        lobj = DBData.get_db_object(prefetched_data, LearningObject, lobj_id)
        children = DBData.filter_db_objects(prefetched_data, LearningObject, parent_id=lobj_id)
        module = DBData.get_db_object(prefetched_data, CourseModule, lobj.course_module_id)
        category = lobj.category

        self.module = precreated.get_or_create_proxy(ModuleEntryBase, module.id)
        if lobj.parent_id is None:
            self.parent = None
        else:
            self.parent = precreated.get_or_create_proxy(ExerciseEntryBase, lobj.parent_id)
        self.category = str(category)
        self.category_id = category.id
        self.category_status = category.status
        self.confirm_the_level = category.confirm_the_level
        self.module_id = module.id
        self.module_status = module.status
        self.id = lobj.id
        self.order = lobj.order
        self.status = lobj.status
        self.name = str(lobj)
        self.hierarchical_name = lobj.hierarchical_name()
        self.number = str(module.order) + '.' + lobj.number()
        self.link = lobj.get_display_url()
        self.submissions_link = lobj.get_submission_list_url()
        self.requirements = [str(r) for r in module.requirements.all()]
        self.opening_time = module.opening_time
        self.reading_opening_time = module.reading_opening_time
        self.closing_time = module.closing_time
        self.late_allowed = module.late_submissions_allowed
        self.late_time = module.late_submission_deadline
        self.late_percent = module.get_late_submission_point_worth()
        self.is_empty = lobj.is_empty()
        self.get_path = lobj.get_path()
        self.children = [precreated.get_or_create_proxy(ExerciseEntryBase, o.id) for o in children]

        if isinstance(lobj, BaseExercise):
            self.submittable = True
            self.points_to_pass = lobj.points_to_pass
            self.difficulty = lobj.difficulty
            self.max_submissions = lobj.max_submissions
            self.max_points = lobj.max_points
            self.allow_assistant_viewing = lobj.allow_assistant_viewing
        else:
            self.submittable = False
            self.points_to_pass = 0
            self.difficulty = ''
            self.max_submissions = 0
            self.max_points = 0
            self.allow_assistant_viewing = False


class ModuleEntryBase(CacheBase, EqById, Generic[ExerciseEntry]):
    KEY_PREFIX: ClassVar[str] = 'module'
    NUM_PARAMS: ClassVar[int] = 1
    INVALIDATORS = [
        (CourseModule, [post_delete, post_save], ("id",)),
        (LearningObject, [post_delete, post_save], ("course_module_id",)),
        (
            LearningObjectCategory,
            [post_delete, post_save],
            category_learning_objects(lambda lobj: [lobj.course_module_id]),
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
    requirements: List[str]
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
    children: List[ExerciseEntry]

    def post_build(self, precreated: ProxyManager):
        if self.children and not isinstance(self.children[0], tuple):
            return

        for i, params in enumerate(self.children):
            self.children[i] = precreated.get_or_create_proxy(ExerciseEntryBase, *params[0])

    def get_proxy_keys(self) -> Iterable[str]:
        return ["children"]

    def get_child_proxies(self) -> Iterable[CacheBase]:
        return self.children

    # pylint: disable-next=arguments-differ too-many-locals
    def _generate_data(
            self,
            precreated: ProxyManager,
            prefetched_data: Optional[DBData] = None,
            ):
        """ Returns object that is cached into self.data """
        module_id = self._params[0]
        module = DBData.get_db_object(prefetched_data, CourseModule, module_id)
        lobjs = DBData.filter_db_objects(prefetched_data, LearningObject, course_module_id=module_id)
        children = DBData.filter_db_objects(
            prefetched_data, LearningObject, parent_id=None, course_module_id=module_id
        )

        self.id = module.id
        self.order = module.order
        self.status = module.status
        self.url = module.url
        self.name = str(module)
        self.number = str(module.order)
        self.introduction = module.introduction
        self.link = module.get_absolute_url()
        self.requirements = [str(r) for r in module.requirements.all()]
        self.opening_time = module.opening_time
        self.reading_opening_time = module.reading_opening_time
        self.closing_time = module.closing_time
        self.late_allowed = module.late_submissions_allowed
        self.late_time = module.late_submission_deadline
        self.late_percent = module.get_late_submission_point_worth()
        self.points_to_pass = module.points_to_pass
        self.children = [precreated.get_or_create_proxy(ExerciseEntryBase, child.id) for child in children]
        self.exercise_count = 0
        self.max_points = 0
        self.max_points_by_difficulty = {}

        for exercise in lobjs:
            if isinstance(exercise, BaseExercise):
                if not exercise.category.confirm_the_level:
                    _add_to(self, exercise)


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


@dataclass
class TotalsBase:
    exercise_count: int = 0
    max_points: int = 0
    max_points_by_difficulty: Dict[str, int] = field(default_factory=dict)
    min_group_size: int = 100000
    max_group_size: int = 1


T = TypeVar("T", bound="CachedDataBase")
class CachedDataBase(CacheBase, Generic[ModuleEntry, ExerciseEntry, CategoryEntry, Totals]):
    KEY_PREFIX: ClassVar[str] = 'instance'
    NUM_PARAMS: ClassVar[int] = 1
    INVALIDATORS = [
        # This technically doesn't invalidate correctly if the instance of
        # a module, exercise or category changes but that should never happen.
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
    created: datetime
    module_index: Dict[int, ModuleEntry]
    exercise_index: Dict[int, ExerciseEntry]
    paths: Dict[int, Dict[str, int]]
    modules: List[ModuleEntry]
    categories: Dict[int, CategoryEntry]
    total: Totals

    def post_build(self, precreated: ProxyManager):
        if self.modules and not isinstance(self.modules[0], tuple):
            return

        for i, module_params in enumerate(self.modules):
            proxy = precreated.get_or_create_proxy(ModuleEntryBase, *module_params[0])
            self.modules[i] = proxy
            self.module_index[module_params[0][0]] = proxy

        for k, exercise_params in self.exercise_index.items():
            self.exercise_index[k] = precreated.get_or_create_proxy(ExerciseEntryBase, *exercise_params[0])

    @classmethod
    def get_for_models(
            cls: Type[T],
            instance: CourseInstance,
            prefetch_children: bool = True,
            prefetched_data: Optional[DBData] = None,
            ) -> T:
        return cls.get(instance.id, prefetch_children=prefetch_children, prefetched_data=prefetched_data)

    @classmethod
    def get(
            cls: Type[T],
            instance_id: int,
            prefetch_children: bool = True,
            prefetched_data: Optional[DBData] = None,
            ) -> T:
        return super().get(instance_id, prefetch_children=prefetch_children, prefetched_data=prefetched_data)

    def get_proxy_keys(self) -> Iterable[str]:
        return ["module_index", "exercise_index", "modules"]

    def get_child_proxies(self) -> Iterable[CacheBase]:
        return self.modules + list(self.exercise_index.values())

    def _generate_data(
            self,
            precreated: ProxyManager,
            prefetched_data: Optional[DBData] = None,
            ):
        """ Returns object that is cached into self.data """
        instance_id = self._params[0]
        if not prefetched_data:
            prefetched_data = DBData()

            instance = CourseInstance.objects.get(id=instance_id)
            module_objs = (
                CourseModule.objects
                .filter(course_instance=instance)
                .prefetch_related(
                    Prefetch(
                        "requirements",
                        queryset=(
                            CourseModuleRequirement.objects
                            .select_related("threshold")
                            .prefetch_related(
                                "passed_modules"
                                "passed_categories",
                                Prefetch(
                                    "passed_exercises",
                                    queryset=BaseExercise.objects.select_related("parent"),
                                ),
                                "points",
                            )
                        )
                    ),
                )
            )
            lobjs = LearningObject.objects.filter(course_module__in=module_objs).prefetch_related("category")

            prefetched_data.add(instance)
            prefetched_data.extend(CourseModule, module_objs)
            prefetched_data.extend(LearningObject, lobjs)
        else:
            module_objs = prefetched_data.filter_db_objects(CourseModule, course_instance_id=instance_id)
            lobjs = [lobj for module in module_objs for lobj in module.learning_objects.all()]

        self.exercise_index = exercise_index = {}
        self.module_index = module_index = {}
        self.paths = paths = {}
        self.modules = modules = []
        self.categories = categories = {}
        self.total = total = TotalsBase()

        for lobj in lobjs:
            exercise_index[lobj.id] = precreated.get_or_create_proxy(ExerciseEntryBase, lobj.id)
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

        precreated.resolve(self.get_child_proxies(), prefetched_data=prefetched_data)

        for entry in exercise_index.values():
            paths[entry.module.id][entry.get_path] = entry.id

        # Augment submittable exercise parameters.
        for exercise in lobjs:
            if isinstance(exercise, BaseExercise):
                entry = exercise_index[exercise.id]
                if not entry.confirm_the_level:
                    _add_to(categories[entry.category_id], exercise)
                    _add_to(total, exercise)

                    if exercise.max_group_size > total.max_group_size:
                        total.max_group_size = exercise.max_group_size
                    if exercise.max_group_size > 1 and exercise.min_group_size < total.min_group_size:
                        total.min_group_size = exercise.min_group_size

        if total.min_group_size > total.max_group_size:
            total.min_group_size = 1

        self.created = timezone.now()
