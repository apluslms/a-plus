from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar, Dict, Generic, List, Literal, Optional, TypeVar


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


@dataclass
class CachedDataBase(Generic[ModuleEntry, ExerciseEntry, CategoryEntry, Totals]):
    created: datetime
    module_index: Dict[int, ModuleEntry]
    exercise_index: Dict[int, ExerciseEntry]
    paths: Dict[int, Dict[str, int]]
    modules: List[ModuleEntry]
    categories: Dict[int, CategoryEntry]
    total: Totals
