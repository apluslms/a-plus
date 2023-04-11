from django.http.response import Http404
from course.models import CourseModule, LearningObjectCategory
from ..models import LearningObject


class NoSuchContent(Exception):
    pass


class HierarchyIterator:
    # pylint: disable-next=too-many-arguments
    def __init__(self, children, idx=None, tree=None, visited=False, enclosed=True):
        if idx is None:
            self._default_start(children)
        else:
            self.idx = idx.copy()
            self.levels = [children]
            if tree and len(tree) > 1:
                for entry in tree[:-1]:
                    self.levels.append(entry['children'])
        self.visited = visited
        self.enclose_begun = not enclosed
        self.enclose_ended = not enclosed

    def __iter__(self): # pylint: disable=non-iterator-returned
        return self


class NextIterator(HierarchyIterator):

    def _default_start(self, children):
        self.idx = [0]
        self.levels = [children]

    def __next__(self):
        if not self.enclose_begun:
            self.enclose_begun = True
            return {'type':'level','down':True}
        i = self.idx[-1]
        level = self.levels[-1]
        if not self.visited:
            if i < len(level):
                self.visited = True
                return level[i]
        else:
            children = level[i].get('children')
            if children:
                self.levels.append(children)
                self.idx.append(0)
                self.visited = False
                return {'type':'level','down':True}
            i += 1
            if i < len(level):
                self.idx[-1] = i
                return level[i]
        if len(self.idx) > 1:
            self.idx = self.idx[:-1]
            self.levels = self.levels[:-1]
            self.idx[-1] += 1
            self.visited = False
            return {'type':'level','up':True}
        if not self.enclose_ended:
            self.enclose_ended = True
            return {'type':'level','up':True}
        raise StopIteration()


class PreviousIterator(HierarchyIterator):

    def _default_start(self, children):
        self.idx = []
        self.levels = []
        self._goto_last(children)

    def _goto_last(self, children):
        level = children
        while level:
            i = len(level) - 1
            self.idx.append(i)
            self.levels.append(level)
            level = level[i].get('children')

    def __next__(self):
        i = self.idx[-1]
        level = self.levels[-1]
        if not self.visited:
            self.visited = True
            return level[i]
        if i > 0:
            i -= 1
            self.idx[-1] = i
            self._goto_last(level[i].get('children'))
            return self.levels[-1][self.idx[-1]]
        if len(self.idx) > 1:
            self.idx = self.idx[:-1]
            self.levels = self.levels[:-1]
            return self.levels[-1][self.idx[-1]]
        raise StopIteration()


class ContentMixin:

    def created(self):
        return self.data['created']

    def total(self):
        return self.data['total']

    def modules(self):
        return self.data['modules']

    def modules_flatted(self):
        for module in self.data['modules']:
            module['flatted'] = self.flat_module(module)
        return self.data['modules']

    def categories(self):
        categories = list(self.data['categories'].values())
        categories.sort(key=lambda entry: entry['name'])
        return categories

    def flat_module(self, module, enclosed=True):
        modules = self.modules()
        idx = self._model_idx(module)
        tree = self._by_idx(modules, idx)
        return NextIterator(tree[0]['children'], enclosed=enclosed)

    def flat_full(self):
        return NextIterator(self.modules(), enclosed=False)

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

    def find_number(self, number):
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

    def find_category(self, category_id):
        categories = self.data['categories']
        if category_id in categories:
            return categories[category_id]
        raise NoSuchContent()

    def find(self, model):
        modules = self.modules()
        idx = self._model_idx(model)
        tree = self._by_idx(modules, idx)
        return (
            tree[-1],
            tree,
            self._previous(idx, tree),
            self._next(idx, tree),
        )

    def search_exercises(self, **kwargs):
        _, entries = self.search_entries(**kwargs)
        return [e for e in entries if e['type'] == 'exercise']

    def search_entries(self, number=None, category_id=None, module_id=None, # noqa: MC0001
                       exercise_id=None, filter_for_assistant=False, best=False, # pylint: disable=unused-argument
                       raise_404=True):
        entry = None
        if number:
            try:
                entry = self.find_number(number)
                if entry['type'] == 'module':
                    module_id = entry['id']
                elif entry['type'] == 'exercise':
                    exercise_id = entry['id']
            except NoSuchContent:
                if raise_404:
                    raise Http404() # pylint: disable=raise-missing-from
                raise
        search = None
        if exercise_id is not None:
            search = { 'type': 'exercise', 'id': int(exercise_id) }
        elif module_id is not None:
            search = { 'type': 'module', 'id': int(module_id) }
        if search:
            try:
                idx = self._model_idx(search)
            except NoSuchContent:
                if raise_404:
                    raise Http404() # pylint: disable=raise-missing-from
                raise
            tree = self._by_idx(self.modules(), idx)
            if not entry:
                entry = tree[-1]
        else:
            tree = [{ 'type': 'all', 'children': self.modules() }]
        exercises = []

        def recursion(entry):
            if (
                entry['type'] == 'module' or ( # pylint: disable=too-many-boolean-expressions
                    entry['type'] == 'exercise' and
                    (category_id is None or entry['category_id'] == category_id) and
                    (not filter_for_assistant or entry['allow_assistant_viewing'])
                )
            ):
                exercises.append(entry)
            for child in entry['children']:
                recursion(child)
        recursion(tree[-1])
        return entry, exercises

    def _previous(self, idx, tree):
        for entry in PreviousIterator(self.modules(), idx, tree, visited=True):
            if self.is_listed(entry):
                return entry
        return None

    def _next(self, idx, tree):
        for entry in NextIterator(self.modules(), idx, tree, visited=True, enclosed=False):
            if self.is_listed(entry):
                return entry
        return None

    def _model_idx(self, model):
        def find(index, search):
            if search in index:
                return index[search]
            raise NoSuchContent()
        entry_type = None
        if isinstance(model, dict):
            entry_type = model.get('type', None)
            if entry_type == 'module':
                return find(self.data['module_index'], model['id'])
            if entry_type == 'exercise':
                return find(self.data['exercise_index'], model['id'])
        elif isinstance(model, CourseModule):
            return find(self.data['module_index'], model.id)
        elif isinstance(model, LearningObject):
            return find(self.data['exercise_index'], model.id)
        else:
            raise NoSuchContent()

    @classmethod
    def _by_idx(cls, hierarchy, idx):
        tree = []
        for i in idx:
            entry = hierarchy[i]
            hierarchy = entry['children']
            tree.append(entry)
        return tree

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
                and entry['status'] != LearningObject.STATUS.UNLISTED
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
