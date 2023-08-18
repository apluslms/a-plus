from __future__ import annotations
from datetime import datetime
from typing import (
    cast,
    Generator,
    Generic,
    Iterable,
    List,
    Literal,
    Optional,
    overload,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)

from django.http.response import Http404

from course.models import CourseModule
from ..models import LearningObject
from .basetypes import CachedDataBase, CategoryEntryBase, LearningObjectEntryBase, ModuleEntryBase, TotalsBase
from .exceptions import NoSuchContent


ExerciseEntry = TypeVar("ExerciseEntry", bound=LearningObjectEntryBase)
ModuleEntry = TypeVar("ModuleEntry", bound=ModuleEntryBase)
CategoryEntry = TypeVar("CategoryEntry", bound=CategoryEntryBase)
Totals = TypeVar("Totals", bound=TotalsBase)


Entry = Union[ExerciseEntry, ModuleEntry]

EE = TypeVar("EE", bound=LearningObjectEntryBase)
ME = TypeVar("ME", bound=ModuleEntryBase)


class LevelMarker:
    def __init__(self, up):
        self.type = "level"
        self.up = up
        self.down = not up


def _get_tree_indices(children: Sequence[Entry[EE,ME]], tree: Sequence[Entry[EE, ME]]) -> List[int]:
    indices = []
    for e in tree:
        indices.append([c.id for c in children].index(e.id))
        children = e.children
    return indices


@overload
def next_iterator(
        children: Sequence[Entry[EE, ME]],
        tree: Optional[Sequence[Entry[EE, ME]]] = None,
        skip_first: bool = False,
        level_markers: Literal[True] = True,
        ) -> Generator[Union[Entry[EE, ME], LevelMarker], None, None]:
    ...
@overload
def next_iterator(
        children: Sequence[Entry[EE, ME]],
        tree: Optional[Sequence[Entry[EE, ME]]] = None,
        skip_first: bool = False,
        level_markers: Literal[False] = True, # type: ignore
        ) -> Generator[Entry[EE, ME], None, None]:
    ...
def next_iterator(
        children: Sequence[Entry[EE, ME]],
        tree: Optional[Sequence[Entry[EE, ME]]] = None,
        skip_first: bool = False,
        level_markers: bool = True,
        ) -> Generator[Union[Entry[EE, ME], LevelMarker], None, None]:
    def descendants(
            entry: Entry[EE, ME],
            start: List[int],
            ) -> Generator[Union[Entry[EE, ME], LevelMarker], None, None]:
        children = entry.children
        if start:
            children = children[start[0]:]
        else:
            yield entry
            if not children:
                return
            if level_markers:
                yield LevelMarker(False)

        for child in children:
            yield from descendants(child, start[1:])
            start = []

        if level_markers:
            yield LevelMarker(True)

    if level_markers:
        yield LevelMarker(False)

    # Get the starting index list of the first entry as specified by tree
    if tree is not None:
        tree_indices = _get_tree_indices(children, tree)
    else:
        tree_indices = [0]

    if skip_first:
        # Move the starting index to the next element
        first_entry = tree[-1] if tree else children[0]
        if first_entry.children:
            tree_indices.append(0)
        else:
            tree_indices[-1] += 1

    children = children[tree_indices[0]:]

    for child in children:
        yield from descendants(child, tree_indices[1:])
        tree_indices = []

    if level_markers:
        yield LevelMarker(True)


def previous_iterator(
        children: Sequence[Entry[EE, ME]],
        tree: Optional[Sequence[Entry[EE, ME]]] = None,
        skip_first: bool = False,
        ) -> Generator[Entry[EE, ME], None, None]:
    def descendants(
            children: Sequence[Entry[EE, ME]],
            start: List[int]
            ) -> Generator[Entry[EE, ME], None, None]:
        if start:
            if len(start) == 1:
                yield children[start[0]]
                children = children[:start[0]]
            else:
                children = children[:start[0]+1]

        for child in reversed(children):
            yield from descendants(child.children, start[1:])
            yield child
            start = []

    def _go_to_last(indices: List[int]):
        nonlocal children
        current = children
        for s in indices:
            current = current[s].children

        while current:
            indices.append(len(current)-1)
            current = current[-1].children

    # Get the starting index list of the first entry as specified by tree
    if tree is not None:
        tree_indices = _get_tree_indices(children, tree)
    else:
        tree_indices = []
        _go_to_last(tree_indices)

    if skip_first:
        # Move the starting index to the previous element
        if tree_indices[-1] == 0:
            tree_indices = tree_indices[-1]
        else:
            tree_indices[-1] -= 1
            _go_to_last(tree_indices)

        if not tree_indices:
            return

    yield from descendants(children, tree_indices)


class ContentMixin(Generic[ModuleEntry, ExerciseEntry, CategoryEntry, Totals]):
    data: CachedDataBase[ModuleEntry, ExerciseEntry, CategoryEntry, Totals]

    def created(self) -> datetime:
        return self.data.created

    def total(self) -> Totals:
        return self.data.total

    def modules(self) -> List[ModuleEntry]:
        return self.data.modules

    def modules_flatted(self) -> List[ModuleEntry]:
        for module in self.data.modules:
            # TODO: this would be better as a cached property on the module entries themselves
            # which would make this whole method unnecessary
            module.flatted = list(self.flat_module(module))
        return self.data.modules

    def exercises(self) -> Iterable[ExerciseEntry]:
        return self.data.exercise_index.values()

    def categories(self):
        categories = list(self.data.categories.values())
        categories.sort(key=lambda entry: entry.name)
        return categories

    @overload
    def flat_module( # pyright: ignore[reportGeneralTypeIssues]
            self,
            module: Union[ModuleEntry, CourseModule],
            level_markers: Literal[True] = True,
            ) -> Iterable[Union[ModuleEntry, ExerciseEntry, LevelMarker]]:
        return [] # Needed for pylint
    @overload
    def flat_module(
            self,
            module: Union[ModuleEntry, CourseModule],
            level_markers: Literal[False] = True, # type: ignore
            ) -> Iterable[Union[ModuleEntry, ExerciseEntry]]:
        ...
    def flat_module(
            self,
            module: Union[ModuleEntry, CourseModule],
            level_markers: bool = True,
            ) -> Iterable[Union[ModuleEntry, ExerciseEntry, LevelMarker]]:
        entry = self.entry_for_model(module)
        children = cast(List[ExerciseEntry], entry.children)
        return next_iterator(
            children,
            level_markers=level_markers, # type: ignore
        )

    @overload
    def flat_full( # pyright: ignore[reportGeneralTypeIssues]
        self,
        level_markers: Literal[True] = True,
        ) -> Iterable[Union[ModuleEntry, ExerciseEntry, LevelMarker]]:
        return [] # Needed for pylint
    @overload
    def flat_full(
            self,
            level_markers: Literal[False] = True, # type: ignore
            ) -> Iterable[Union[ModuleEntry, ExerciseEntry]]:
        ...
    def flat_full(self, level_markers = True):
        return next_iterator(
            self.modules(),
            level_markers=level_markers, # type: ignore
        )

    def begin(self) -> Optional[ExerciseEntry]:
        for entry in self.flat_full(level_markers=False):
            if isinstance(entry, LearningObjectEntryBase):
                return entry
        return None

    def find_path(self, module_id, path):
        paths = self.data.paths.get(module_id, {})
        if path in paths:
            return paths[path]
        raise NoSuchContent()

    def find_number(self, number: str) -> Union[ModuleEntry, ExerciseEntry]:
        """Find item by a period separated list of order numbers

        E.g. number="3.2.5" takes the fifth learning object in the second
        learning object of the third module
        """
        def find(
                search: Sequence[Union[ModuleEntry, ExerciseEntry]],
                number: str,
                ) -> Union[ModuleEntry, ExerciseEntry]:
            for s in search:
                if s.number == number:
                    return s
            raise NoSuchContent()

        parts = number.split('.')
        number = parts[0]
        hit = find(self.modules(), number)
        for part in parts[1:]:
            number += "." + part
            hit = find(cast(List[ExerciseEntry], hit.children), number)

        return hit

    def find_category(self, category_id: int) -> CategoryEntry:
        categories = self.data.categories
        if category_id in categories:
            return categories[category_id]
        raise NoSuchContent()

    def find(
            self,
            model: Union[LearningObject, CourseModule],
            ) -> Tuple[
                Union[ModuleEntry, ExerciseEntry],
                List[Union[ModuleEntry, ExerciseEntry]],
                Optional[Union[ModuleEntry, ExerciseEntry]],
                Optional[Union[ModuleEntry, ExerciseEntry]]
            ]:
        entry = self.entry_for_model(model)
        tree = self._tree(entry)
        return (
            entry,
            tree,
            self._previous(tree),
            self._next(tree),
        )

    def get_absolute_order_number(self, learning_object_id: int) -> int:
        """Get the absolute order number of the given learning object
        (i.e. how manieth chapter or exercise it is in the material).
        """
        def inner(parent: Union[ModuleEntry, ExerciseEntry], n: int) -> Tuple[bool, int]:
            # parent is a cached dict representing a CourseModule or a LearningObject
            for entry in parent.children:
                n += 1
                if entry.id == learning_object_id:
                    return True, n
                found, n = inner(entry, n)
                if found:
                    return True, n
            return False, n

        n = 0
        for module in self.modules():
            found, n = inner(module, n)
            if found:
                return n

    def _tree(self, entry: Union[ModuleEntry, ExerciseEntry]) -> List[Union[ModuleEntry, ExerciseEntry]]:
        if isinstance(entry, ModuleEntryBase):
            return [entry]

        module = entry.module
        tree = []
        while entry is not None:
            tree.append(entry)
            entry = entry.parent # type: ignore

        tree.append(module)

        tree.reverse()
        return tree

    def entry_for_model(
            self,
            model: Union[ModuleEntry, ExerciseEntry, LearningObject, CourseModule]
            ) -> Union[ModuleEntry, ExerciseEntry]:
        if isinstance(model, ModuleEntryBase):
            return self.get_module(model.id)
        if isinstance(model, LearningObjectEntryBase):
            return self.get_exercise(model.id)
        if isinstance(model, CourseModule):
            return self.get_module(model.id)
        if isinstance(model, LearningObject):
            return self.get_exercise(model.id)

        raise NoSuchContent()

    def entry_for_exercise(self, model: LearningObject) -> ExerciseEntry:
        return self.get_exercise(model.id)

    def get_exercise(self, exercise_id: int) -> ExerciseEntry:
        if exercise_id in self.data.exercise_index:
            return self.data.exercise_index[exercise_id]
        raise NoSuchContent()

    def entry_for_module(self, model: CourseModule) -> ModuleEntry:
        return self.get_module(model.id)

    def get_module(self, module_id: int) -> ModuleEntry:
        if module_id in self.data.module_index:
            return self.data.module_index[module_id]
        raise NoSuchContent()

    def search_exercises(self, **kwargs) -> List[LearningObjectEntryBase]:
        _, entries = self.search_entries(**kwargs)
        return [e for e in entries if isinstance(e, LearningObjectEntryBase)]

    def search_entries( # pylint: disable=too-many-arguments
            self,
            number: Optional[str] = None,
            category_id: Optional[int] = None,
            module_id: Optional[int] = None, # noqa: MC0001
            exercise_id: Optional[int] = None,
            filter_for_assistant: bool = False,
            best: bool = False, # pylint: disable=unused-argument
            raise_404: bool = True,
            ) -> Tuple[
                Optional[Union[ModuleEntry, ExerciseEntry]],
                List[Union[ModuleEntry, ExerciseEntry]]
            ]:
        """Returns an entry and its filtered descendants.

        The entry is specified using number, module_id or exercise_id.
        category_id and filter_for_assistant are used to filter the descendants"""
        entry = None
        try:
            if number:
                try:
                    entry = self.find_number(number)
                except NoSuchContent:
                    if raise_404:
                        raise Http404() # pylint: disable=raise-missing-from
                    raise
            elif exercise_id is not None:
                entry = self.get_exercise(exercise_id)
            elif module_id is not None:
                entry = self.get_module(module_id)
        except NoSuchContent:
            if raise_404:
                raise Http404() # pylint: disable=raise-missing-from
            raise

        entries = []

        def search_descendants(entry: Union[ExerciseEntry, ModuleEntry]) -> None:
            if (
                isinstance(entry, ModuleEntryBase) or ( # pylint: disable=too-many-boolean-expressions
                    isinstance(entry, LearningObjectEntryBase) and
                    (category_id is None or entry.category_id == category_id) and
                    (not filter_for_assistant or entry.allow_assistant_viewing)
                )
            ):
                entries.append(entry) # type: ignore

            for child in entry.children:
                search_descendants(child)

        if entry:
            search_descendants(entry)
        else:
            for entry in self.modules():
                search_descendants(entry)

        return entry, entries

    def _previous(self, tree: List[Union[ExerciseEntry, ModuleEntry]]) -> Optional[Union[ExerciseEntry, ModuleEntry]]:
        for entry in previous_iterator(self.modules(), tree, skip_first=True):
            if entry.is_listed():
                return entry
        return None

    def _next(self, tree: List[Union[ExerciseEntry, ModuleEntry]]) -> Optional[Union[ExerciseEntry, ModuleEntry]]:
        for entry in next_iterator(self.modules(), tree, skip_first=True, level_markers=False):
            if entry.is_listed():
                return entry
        return None
