from datetime import datetime
from typing import (
    Generator,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from django.http.response import Http404

from course.models import CourseModule, LearningObjectCategory
from ..models import LearningObject
from .basetypes import CachedDataBase, CategoryEntryBase, ExerciseEntryBase, ModuleEntryBase, TotalsBase


class LevelMarker:
    def __init__(self, up):
        self.type = "level"
        self.up = up
        self.down = not up


class NoSuchContent(Exception):
    pass


def _get_tree_indices(children: Sequence[Union[ExerciseEntryBase, ModuleEntryBase]], tree: Sequence[Union[ExerciseEntryBase, ModuleEntryBase]]) -> List[int]:
    indices = []
    for e in tree:
        indices.append([c.id for c in children].index(e.id))
        children = e.children
    return indices


def next_iterator(
        children: Sequence[Union[ExerciseEntryBase, ModuleEntryBase]],
        tree: Optional[Sequence[Union[ExerciseEntryBase, ModuleEntryBase]]] = None,
        skip_first: bool = False,
        enclosed: bool = True,
        ) -> Generator[Union[ExerciseEntryBase, ModuleEntryBase, LevelMarker], None, None]:
    def descendants(entry: Union[ExerciseEntryBase, ModuleEntryBase], start: List[int]) -> Generator[Union[ExerciseEntryBase, ModuleEntryBase, LevelMarker], None, None]:
        children = entry.children
        if start:
            children = children[start[0]:]
        else:
            yield entry
            if not children:
                return
            yield LevelMarker(False)

        for child in children:
            yield from descendants(child, start[1:])
            start = []

        yield LevelMarker(True)

    if enclosed:
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

    if enclosed:
        yield LevelMarker(True)


def previous_iterator(
        children: Sequence[Union[ExerciseEntryBase, ModuleEntryBase]],
        tree: Optional[Sequence[Union[ExerciseEntryBase, ModuleEntryBase]]] = None,
        skip_first: bool = False,
        ) -> Generator[Union[ExerciseEntryBase, ModuleEntryBase], None, None]:
    def descendants(
            children: Sequence[Union[ExerciseEntryBase, ModuleEntryBase]],
            start: List[int]
            ) -> Generator[Union[ExerciseEntryBase, ModuleEntryBase], None, None]:
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


class ContentMixin:
    data: CachedDataBase

    def created(self) -> datetime:
        return self.data.created

    def total(self) -> TotalsBase:
        return self.data.total

    def modules(self) -> List[ModuleEntryBase]:
        return self.data.modules

    def modules_flatted(self) -> List[ModuleEntryBase]:
        for module in self.data.modules:
            # TODO: this would be better as a cached property on the module entries themselves
            # which would make this whole method unnecessary
            module.flatted = list(self.flat_module(module))
        return self.data.modules

    def exercises(self) -> Iterable[ExerciseEntryBase]:
        return self.data.exercise_index.values()

    def categories(self):
        categories = list(self.data.categories.values())
        categories.sort(key=lambda entry: entry.name)
        return categories

    def flat_module(
            self,
            module: Union[ModuleEntryBase, CourseModule],
            enclosed: bool = True,
            ) -> Iterator[Union[ModuleEntryBase, ExerciseEntryBase, LevelMarker]]:
        entry = self.entry_for_model(module)
        return next_iterator(entry.children, enclosed=enclosed)

    def flat_full(self):
        return next_iterator(self.modules(), enclosed=False)

    def begin(self):
        for entry in self.flat_full():
            if entry.type == 'exercise':
                return entry
        return None

    def find_path(self, module_id, path):
        paths = self.data.paths.get(module_id, {})
        if path in paths:
            return paths[path]
        raise NoSuchContent()

    def find_number(self, number: str) -> Union[ModuleEntryBase, ExerciseEntryBase]:
        """Find item by a period separated list of order numbers

        E.g. number="3.2.5" takes the fifth learning object in the second
        learning object of the third module
        """
        hit = None
        search = self.modules()
        parts = number.split('.')
        for i in range(len(parts)):
            number = '.'.join(parts[0:i+1])
            for s in search:
                if s.number == number:
                    hit = s
                    search = hit.children
                    break
            else:
                raise NoSuchContent()
        return hit

    def find_category(self, category_id: int) -> CategoryEntryBase:
        categories = self.data.categories
        if category_id in categories:
            return categories[category_id]
        raise NoSuchContent()

    def find(
            self,
            model: Union[LearningObject, CourseModule],
            ) -> Tuple[
                Union[ModuleEntryBase, ExerciseEntryBase],
                List[Union[ModuleEntryBase, ExerciseEntryBase]],
                Optional[Union[ModuleEntryBase, ExerciseEntryBase]],
                Optional[Union[ModuleEntryBase, ExerciseEntryBase]]
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
        def inner(parent: Union[ModuleEntryBase, ExerciseEntryBase], n: int) -> Tuple[bool, int]:
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

    def _tree(self, entry: Union[ModuleEntryBase, ExerciseEntryBase]) -> List[Union[ModuleEntryBase, ExerciseEntryBase]]:
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
            model: Union[ModuleEntryBase, ExerciseEntryBase, LearningObject, CourseModule]
            ) -> Union[ModuleEntryBase, ExerciseEntryBase]:
        if isinstance(model, ModuleEntryBase):
            return self.get_module(model.id)
        elif isinstance(model, ExerciseEntryBase):
            return self.get_exercise(model.id)
        elif isinstance(model, CourseModule):
            return self.get_module(model.id)
        elif isinstance(model, LearningObject):
            return self.get_exercise(model.id)

        raise NoSuchContent()

    def get_exercise(self, id: int) -> ExerciseEntryBase:
        if id in self.data.exercise_index:
            return self.data.exercise_index[id]
        raise NoSuchContent()

    def get_module(self, id: int) -> ModuleEntryBase:
        if id in self.data.module_index:
            return self.data.module_index[id]
        raise NoSuchContent()

    def search_exercises(self, **kwargs) -> List[ExerciseEntryBase]:
        _, entries = self.search_entries(**kwargs)
        return [e for e in entries if e.type == 'exercise']

    def search_entries(
            self,
            number: Optional[str] = None,
            category_id: Optional[int] = None,
            module_id: Optional[str] = None, # noqa: MC0001
            exercise_id: Optional[str] = None,
            filter_for_assistant: bool = False,
            best: bool = False, # pylint: disable=unused-argument
            raise_404: bool = True,
            ) -> Tuple[
                Optional[Union[ModuleEntryBase, ExerciseEntryBase]],
                List[Union[ModuleEntryBase, ExerciseEntryBase]]
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
                entry = self.get_exercise(int(exercise_id))
            elif module_id is not None:
                entry = self.get_module(int(module_id))
        except NoSuchContent:
            if raise_404:
                raise Http404() # pylint: disable=raise-missing-from
            raise

        entries = []

        def search_descendants(entry: Union[ExerciseEntryBase, ModuleEntryBase]) -> None:
            if (
                isinstance(entry, ModuleEntryBase) or ( # pylint: disable=too-many-boolean-expressions
                    isinstance(entry, ExerciseEntryBase) and
                    (category_id is None or entry.category_id == category_id) and
                    (not filter_for_assistant or entry.allow_assistant_viewing)
                )
            ):
                entries.append(entry)

            for entry in entry.children:
                search_descendants(entry)

        if entry:
            search_descendants(entry)
        else:
            for entry in self.modules():
                search_descendants(entry)

        return entry, entries

    def _previous(self, tree: List[Union[ExerciseEntryBase, ModuleEntryBase]]) -> Optional[Union[ExerciseEntryBase, ModuleEntryBase]]:
        for entry in previous_iterator(self.modules(), tree, skip_first=True):
            if self.is_listed(entry):
                return entry
        return None

    def _next(self, tree: List[Union[ExerciseEntryBase, ModuleEntryBase]]) -> Optional[Union[ExerciseEntryBase, ModuleEntryBase]]:
        # TODO: does the type: level entries cause potential bugs?
        for entry in next_iterator(self.modules(), tree, skip_first=True, enclosed=False):
            if self.is_listed(entry):
                return entry
        return None

    @classmethod
    def _add_by_difficulty(cls, to, difficulty, points):
        if difficulty in to:
            to[difficulty] += points
        else:
            to[difficulty] = points

    @classmethod
    def is_visible(cls, entry):
        t = entry.type
        if t == 'exercise':
            return (
                entry.category_status != LearningObjectCategory.STATUS.HIDDEN
                and entry.module_status != CourseModule.STATUS.HIDDEN
                and not entry.status in (
                    LearningObject.STATUS.HIDDEN,
                    LearningObject.STATUS.ENROLLMENT,
                    LearningObject.STATUS.ENROLLMENT_EXTERNAL,
                )
            )
        if t == 'module':
            return entry.status != CourseModule.STATUS.HIDDEN
        if t == 'category':
            return not entry.status in (
                LearningObjectCategory.STATUS.HIDDEN,
                LearningObjectCategory.STATUS.NOTOTAL,
            )
        return False

    @classmethod
    def is_listed(cls, entry):
        if not cls.is_visible(entry):
            return False
        t = entry.type
        if t == 'exercise':
            return (
                entry.category_status != LearningObjectCategory.STATUS.HIDDEN
                and entry.module_status != CourseModule.STATUS.UNLISTED
                and not entry.status in (
                    LearningObject.STATUS.UNLISTED,
                    LearningObject.STATUS.MAINTENANCE,
                )
            )
        if t == 'module':
            return entry.status != CourseModule.STATUS.UNLISTED
        if t == 'category':
            return entry.status != LearningObjectCategory.STATUS.HIDDEN
        return True

    @classmethod
    def is_in_maintenance(cls, entry):
        t = entry.type
        if t == 'exercise':
            return (
                entry.module_status == CourseModule.STATUS.MAINTENANCE
                or entry.status == LearningObject.STATUS.MAINTENANCE
            )
        if t == 'module':
            return entry.status == CourseModule.STATUS.MAINTENANCE
        return False
