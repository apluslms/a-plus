from typing import Any, Dict, Generator, Iterable, List, Optional, Tuple, Union

from django.http.response import Http404

from course.models import CourseModule, LearningObjectCategory
from ..models import LearningObject


Entry = Dict[str, Any]


class NoSuchContent(Exception):
    pass


def _get_tree_indices(children: List[Entry], tree: List[Entry]) -> List[int]:
    indices = []
    for e in tree:
        indices.append([c["id"] for c in children].index(e["id"]))
        children = e["children"]
    return indices


def next_iterator(
        children: List[Entry],
        tree: Optional[List[Entry]] = None,
        skip_first: bool = False,
        enclosed: bool = True,
        ) -> Generator[Entry, None, None]:
    def descendants(entry, start: List[int]) -> Generator[Entry, None, None]:
        children = entry.get("children", [])
        if start:
            children = children[start[0]:]
        else:
            yield entry
            if not children:
                return
            yield {'type':'level','down':True}

        for child in children:
            yield from descendants(child, start[1:])

        yield {'type':'level','up':True}

    if enclosed:
        yield {'type':'level','down':True}

    # Get the starting index list of the first entry as specified by tree
    if tree is not None:
        tree_indices = _get_tree_indices(children, tree)
    else:
        tree_indices = [0]

    if skip_first:
        # Move the starting index to the next element
        first_entry = tree[-1] if tree else children[0]
        if first_entry.get("children"):
            tree_indices.append(0)
        else:
            tree_indices[-1] += 1

    children = children[tree_indices[0]:]

    for child in children:
        yield from descendants(child, tree_indices[1:])

    if enclosed:
        yield {'type':'level','up':True}


def previous_iterator(
        children: List[Entry],
        tree: Optional[List[Entry]] = None,
        skip_first: bool = False,
        ) -> Generator[Entry, None, None]:
    def descendants(children, start: List[int]) -> Generator[Entry, None, None]:
        if start:
            if len(start) == 1:
                yield children[start[0]]
                children = children[:start[0]]
            else:
                children = children[:start[0]+1]

        for child in reversed(children):
            yield from descendants(child.get("children", []), start[1:])
            yield child

    def _go_to_last(indices: List[int]):
        nonlocal children
        current = children
        for s in indices:
            current = current[s]["children"]

        while current:
            indices.append(len(current)-1)
            current = current[-1].get("children", [])

    # Get the starting index list of the first entry as specified by tree
    if tree is not None:
        tree_indices = _get_tree_indices(children, tree)
    else:
        tree_indices = []
        _go_to_last(tree_indices)

    if skip_first:
        # Move the starting index to the previous element
        while tree_indices[-1] == 0:
            tree_indices = tree_indices[:-1]
        if not tree_indices:
            return
        tree_indices[-1] -= 1
        _go_to_last(tree_indices)

    yield from descendants(children, tree_indices)


class ContentMixin:

    def created(self):
        return self.data['created']

    def total(self):
        return self.data['total']

    def modules(self):
        return self.data['modules']

    def modules_flatted(self):
        for module in self.data['modules']:
            module['flatted'] = list(self.flat_module(module))
        return self.data['modules']

    def exercises(self) -> Iterable[Entry]:
        return self.data["exercise_index"].values()

    def categories(self):
        categories = list(self.data['categories'].values())
        categories.sort(key=lambda entry: entry['name'])
        return categories

    def flat_module(self, module: Union[Entry, CourseModule], enclosed: bool = True):
        entry = self.entry_for_model(module)
        return next_iterator(entry['children'], enclosed=enclosed)

    def flat_full(self):
        return next_iterator(self.modules(), enclosed=False)

    def begin(self):
        for entry in self.flat_full():
            if entry['type'] == 'exercise':
                return entry
        return None

    def find_path(self, module_id, path):
        paths = self.data['paths'].get(module_id, {})
        if path in paths:
            return paths[path]
        raise NoSuchContent()

    def find_number(self, number: str) -> Entry:
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
                if s['number'] == number:
                    hit = s
                    search = hit['children']
                    break
            else:
                raise NoSuchContent()
        return hit

    def find_category(self, category_id: int) -> Entry:
        categories = self.data['categories']
        if category_id in categories:
            return categories[category_id]
        raise NoSuchContent()

    def find(
            self,
            model: Union[LearningObject, CourseModule],
             ) -> Tuple[Entry, List[Entry], Optional[Entry], Optional[Entry]]:
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
        def inner(parent: dict, n: int) -> Tuple[bool, int]:
            # parent is a cached dict representing a CourseModule or a LearningObject
            for entry in parent['children']:
                n += 1
                if entry['id'] == learning_object_id:
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

    def _tree(self, entry: Entry) -> List[Entry]:
        module = entry.get("module")
        tree = []
        while entry is not None:
            tree.append(entry)
            entry = entry["parent"]

        if module is not None:
            tree.append(module)

        tree.reverse()
        return tree

    def entry_for_model(self, model: Union[Entry, LearningObject, CourseModule]) -> Entry:
        if isinstance(model, dict):
            entry_type = model.get('type', None)
            if entry_type == 'module':
                return self.get_module(model['id'])
            if entry_type == 'exercise':
                return self.get_exercise(model['id'])
        elif isinstance(model, CourseModule):
            return self.get_module(model.id)
        elif isinstance(model, LearningObject):
            return self.get_exercise(model.id)

        raise NoSuchContent()

    def get_exercise(self, id: int) -> Entry:
        if id in self.data['exercise_index']:
            return self.data['exercise_index'][id]
        raise NoSuchContent()

    def get_module(self, id: int) -> Entry:
        if id in self.data['module_index']:
            return self.data['module_index'][id]
        raise NoSuchContent()

    def search_exercises(self, **kwargs):
        _, entries = self.search_entries(**kwargs)
        return [e for e in entries if e['type'] == 'exercise']

    def search_entries(
            self,
            number: Optional[str] = None,
            category_id: Optional[int] = None,
            module_id: Optional[str] = None, # noqa: MC0001
            exercise_id: Optional[str] = None,
            filter_for_assistant: bool = False,
            best: bool = False, # pylint: disable=unused-argument
            raise_404: bool = True,
            ) -> Tuple[Optional[Entry], List[Entry]]:
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

        def search_descendants(entry: Entry) -> None:
            if (
                entry['type'] == 'module' or ( # pylint: disable=too-many-boolean-expressions
                    entry['type'] == 'exercise' and
                    (category_id is None or entry['category_id'] == category_id) and
                    (not filter_for_assistant or entry['allow_assistant_viewing'])
                )
            ):
                entries.append(entry)
            for child in entry['children']:
                search_descendants(child)

        if entry:
            search_descendants(entry)
        else:
            search_descendants({ 'type': 'all', 'children': self.modules() })

        return entry, entries

    def _previous(self, tree: List[Entry]) -> Optional[Entry]:
        for entry in previous_iterator(self.modules(), tree, skip_first=True):
            if self.is_listed(entry):
                return entry
        return None

    def _next(self, tree: List[Entry]) -> Optional[Entry]:
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
        t = entry['type']
        if t == 'exercise':
            return (
                entry.get('category_status') != LearningObjectCategory.STATUS.HIDDEN
                and entry.get('module_status') != CourseModule.STATUS.HIDDEN
                and not entry['status'] in (
                    LearningObject.STATUS.HIDDEN,
                    LearningObject.STATUS.ENROLLMENT,
                    LearningObject.STATUS.ENROLLMENT_EXTERNAL,
                )
            )
        if t == 'module':
            return entry['status'] != CourseModule.STATUS.HIDDEN
        if t == 'category':
            return not entry['status'] in (
                LearningObjectCategory.STATUS.HIDDEN,
                LearningObjectCategory.STATUS.NOTOTAL,
            )
        return False

    @classmethod
    def is_listed(cls, entry):
        if not cls.is_visible(entry):
            return False
        t = entry['type']
        if t == 'exercise':
            return (
                entry.get('category_status') != LearningObjectCategory.STATUS.HIDDEN
                and entry.get('module_status') != CourseModule.STATUS.UNLISTED
                and not entry['status'] in (
                    LearningObject.STATUS.UNLISTED,
                    LearningObject.STATUS.MAINTENANCE,
                )
            )
        if t == 'module':
            return entry['status'] != CourseModule.STATUS.UNLISTED
        if t == 'category':
            return entry['status'] != LearningObjectCategory.STATUS.HIDDEN
        return True

    @classmethod
    def is_in_maintenance(cls, entry):
        t = entry['type']
        if t == 'exercise':
            return (
                entry['module_status'] == CourseModule.STATUS.MAINTENANCE
                or entry['status'] == LearningObject.STATUS.MAINTENANCE
            )
        if t == 'module':
            return entry['status'] == CourseModule.STATUS.MAINTENANCE
        return False
