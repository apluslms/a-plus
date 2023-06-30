from __future__ import annotations
from dataclasses import dataclass, field, InitVar
from datetime import datetime
from typing import Any, ClassVar, Dict, Generic, Iterable, List, Literal, Optional, Type, TypeVar, Union

from django.utils import timezone

from course.models import CourseInstance, CourseModule
from lib.cache.cached import CacheBase, DBData, PrecreatedProxies
from ..models import BaseExercise, LearningObject


def add_by_difficulty(to: Dict[str, int], difficulty: str, points: int):
    if difficulty in to:
        to[difficulty] += points
    else:
        to[difficulty] = points


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


@dataclass(eq=False)
class ExerciseEntryBase(EqById, Generic[ModuleEntry, ExerciseEntry]):
    type: ClassVar[Literal['exercise']] = 'exercise'
    # Disable repr for ancestors so there are no infinite loops
    module: ModuleEntry = field(repr=False)
    parent: Optional[ExerciseEntry] = field(repr=False)
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
    submittable: bool
    points_to_pass: int = 0
    difficulty: str = ''
    max_submissions: int = 0
    max_points: int = 0
    allow_assistant_viewing: bool = False
    children: List[ExerciseEntryBase] = field(default_factory=list)


@dataclass(eq=False)
class ModuleEntryBase(EqById, Generic[ExerciseEntry]):
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
    exercise_count: int = 0
    max_points: int = 0
    max_points_by_difficulty: Dict[str, int] = field(default_factory=dict)
    children: List[ExerciseEntry] = field(default_factory=list)


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
@dataclass
class CachedDataBase(CacheBase, Generic[ModuleEntry, ExerciseEntry, CategoryEntry, Totals]):
    KEY_PREFIX: ClassVar[str] = 'instance'
    instance_id: InitVar[int]
    created: datetime
    module_index: Dict[int, ModuleEntry]
    exercise_index: Dict[int, ExerciseEntry]
    paths: Dict[int, Dict[str, int]]
    modules: List[ModuleEntry]
    categories: Dict[int, CategoryEntry]
    total: Totals

    def __post_init__(self, instance_id: int):
        self._resolved = True
        self._params = (instance_id,)

    def post_get(self, precreated: PrecreatedProxies):
        pass

    def _generate_data(
            self,
            precreated: Optional[PrecreatedProxies] = None,
            prefetched_data: Optional[DBData] = None,
            ):
        """ Returns object that is cached into self.data """
        instance_id = self._params[0]
        instance = DBData.get_db_object(prefetched_data, CourseInstance, instance_id)
        if not prefetched_data:
            module_objs = CourseModule.objects.filter(course_instance=instance).prefetch_related(
                'requirements',
                'requirements__threshold__passed_modules',
                'requirements__threshold__passed_categories',
                'requirements__threshold__passed_exercises',
                'requirements__threshold__passed_exercises__parent',
                'requirements__threshold__points',
                'learning_objects',
            )
            lobjs = LearningObject.objects.filter(course_module__in=module_objs).prefetch_related("children", "category")
        else:
            module_objs = prefetched_data.filter_db_objects(CourseModule, course_instance_id=instance_id)
            lobjs = prefetched_data.filter_db_objects(LearningObject, course_module__in=module_objs)

        self.exercise_index = exercise_index = {}
        self.module_index = module_index = {}
        self.paths = paths = {}
        self.modules = modules = []
        self.categories = categories = {}
        self.total = total = TotalsBase()

        def recursion(
                module: ModuleEntryBase,
                objects: Iterable[LearningObject],
                parents: List[LearningObject],
                container: List[ExerciseEntryBase],
                ) -> None:
            """ Recursively travels exercises hierarchy """
            parent_id = parents[-1].id if parents else None
            children = [o for o in objects if o.parent_id == parent_id]
            j = 0
            for o in children:
                o._parents = parents + [o]
                category = o.category
                entry = ExerciseEntryBase(
                    module = module,
                    parent = exercise_index[parent_id] if parent_id is not None else None,
                    category = str(category),
                    category_id = category.id,
                    category_status = category.status,
                    confirm_the_level = category.confirm_the_level,
                    module_id = module.id,
                    module_status = module.status,
                    id = o.id,
                    order = o.order,
                    status = o.status,
                    name = str(o),
                    hierarchical_name = o.hierarchical_name(),
                    number = module.number + '.' + o.number(),
                    link = o.get_display_url(),
                    submittable = False,
                    submissions_link = o.get_submission_list_url(),
                    requirements = module.requirements,
                    opening_time = module.opening_time,
                    reading_opening_time = module.reading_opening_time,
                    closing_time = module.closing_time,
                    late_allowed = module.late_allowed,
                    late_time = module.late_time,
                    late_percent = module.late_percent,
                    is_empty = o.is_empty(),
                    get_path = o.get_path(),
                )
                container.append(entry)
                exercise_index[o.id] = entry
                paths[module.id][o.get_path()] = o.id
                if category.id not in categories:
                    categories[category.id] = CategoryEntryBase(
                        id = category.id,
                        status = category.status,
                        name = str(category),
                        points_to_pass = category.points_to_pass,
                    )
                recursion(module, objects, o._parents, entry.children)
                j += 1

        # Collect each module.
        i = 0
        for module in module_objs:
            entry = ModuleEntryBase(
                id = module.id,
                order = module.order,
                status = module.status,
                url = module.url,
                name = str(module),
                number = str(module.order),
                introduction = module.introduction,
                link = module.get_absolute_url(),
                requirements = [str(r) for r in module.requirements.all()],
                opening_time = module.opening_time,
                reading_opening_time = module.reading_opening_time,
                closing_time = module.closing_time,
                late_allowed = module.late_submissions_allowed,
                late_time = module.late_submission_deadline,
                late_percent = module.get_late_submission_point_worth(),
                points_to_pass = module.points_to_pass,
            )
            modules.append(entry)
            module_index[module.id] = entry
            paths[module.id] = {}
            recursion(entry, lobjs, [], entry.children)
            i += 1

        # Augment submittable exercise parameters.
        def add_to(target: Union[ModuleEntryBase, CategoryEntryBase, TotalsBase], exercise: BaseExercise) -> None:
            target.exercise_count += 1
            target.max_points += exercise.max_points
            add_by_difficulty(
                target.max_points_by_difficulty,
                exercise.difficulty,
                exercise.max_points
            )
        for exercise in lobjs:
            if isinstance(exercise, BaseExercise):
                entry = exercise_index[exercise.id]

                entry.submittable = True
                entry.points_to_pass = exercise.points_to_pass
                entry.difficulty = exercise.difficulty
                entry.max_submissions = exercise.max_submissions
                entry.max_points = exercise.max_points
                entry.allow_assistant_viewing = exercise.allow_assistant_viewing

                if not entry.confirm_the_level:
                    add_to(entry.module, exercise)
                    add_to(categories[exercise.category.id], exercise)
                    add_to(total, exercise)

                    if exercise.max_group_size > total.max_group_size:
                        total.max_group_size = exercise.max_group_size
                    if exercise.max_group_size > 1 and exercise.min_group_size < total.min_group_size:
                        total.min_group_size = exercise.min_group_size

        if total.min_group_size > total.max_group_size:
            total.min_group_size = 1

        self.created = timezone.now()
