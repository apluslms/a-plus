from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.util import timezone

from course.models import CourseInstance, CourseModule
from exercise.models import LearningObject
from .abstract import CachedAbstract


class NoSuchContent(Exception):
    pass


class CachedContent(CachedAbstract):
    """ Course content hierarchy for template presentations """
    KEY_PREFIX = 'content'

    def __init__(self, course_instance):
        self.instance = course_instance
        super().__init__(course_instance)

    def _generate_data(self, instance):
        """ Returns object that is cached into self.data """
        module_index = {}
        exercise_index = {}
        paths = {}
        flat = []

        for module in instance.course_modules.all():
            flat.append({
                'has_children': False,
                'close_levels': [],
                'type': 'module',
                'hidden': not module.status in (CourseModule.STATUS.READY, CourseModule.STATUS.MAINTENANCE),
                'maintenance': module.status == CourseModule.STATUS.MAINTENANCE,
                'name': str(module),
                'link': module.get_absolute_url(),
                'opening_time': module.opening_time,
                'closing_time': module.closing_time,
            })
            module_index[module.id] = len(flat) - 1
            paths[module.id] = {}
            self._generate_recursion(
                flat,
                exercise_index,
                paths,
                module,
                list(module.learning_objects.all()),
                [],
                None
            )

        return {
            'created': timezone.now(),
            'module_index': module_index,
            'exercise_index': exercise_index,
            'paths': paths,
            'flat': flat,
        }

    def _generate_recursion(self, flat, index, paths, module, objects, parents, parent_id):
        children = [o for o in objects if o.parent_id == parent_id]
        if children:
            flat[-1]['has_children'] = True
            for o in children:
                o._parents = parents + [o]
                flat.append({
                    'has_children': False,
                    'close_levels': [],
                    'type': 'exercise',
                    'hidden': not o.status in (LearningObject.STATUS.READY, LearningObject.STATUS.MAINTENANCE),
                    'maintenance': o.status == LearningObject.STATUS.MAINTENANCE,
                    'name': str(o),
                    'link': o.get_absolute_url(),
                    'breadcrumb': [index[o.id] for o in o._parents[:-1]],
                    'opening_time': module.opening_time,
                    'closing_time': module.closing_time,
                    'is_empty': o.is_empty(),
                })
                index[o.id] = len(flat) - 1
                paths[module.id][o.get_path()] = o.id
                self._generate_recursion(flat, index, paths, module, objects, o._parents, o.id)
            flat[-1]['close_levels'].append(True)

    def created(self):
        return self.data['created']

    def full_hierarchy(self):
        return self.data['flat']

    def children_hierarchy(self, model):
        i = self._index_model(model)
        full = self.full_hierarchy()
        children = []
        model = full[i]
        if model['has_children']:
            level = 1
            i += 1
            while level > 0:
                model = full[i]
                if model['has_children']:
                    level += 1
                children.append(model)
                i += 1
                level -= len(model['close_levels'])
        return children

    def find_path(self, module_id, path):
        paths = self.data['paths'].get(module_id, {})
        if path in paths:
            return paths[path]
        raise NoSuchContent()

    def find(self, model):
        i = self._index_model(model)
        full = self.full_hierarchy()
        return self._previous(full, i), full[i], self._next(full, i)

    def breadcrumb(self, model):
        i = self._index_model(model)
        full = self.full_hierarchy()
        return [full[j] for j in full[i]['breadcrumb']]

    def _index_model(self, model):
        if isinstance(model, CourseModule):
            return self._index_dict(self.data['module_index'], model.id)
        elif isinstance(model, LearningObject):
            return self._index_dict(self.data['exercise_index'], model.id)
        else:
            raise NoSuchContent()

    def _index_dict(self, index, search):
        if search in index:
            return index[search]
        raise NoSuchContent()

    def _previous(self, full, index):
        i = index - 1
        while i >= 0:
            entry = full[i]
            if self._is_visible(entry):
                return entry
            i -= 1
        return None

    def _next(self, full, index):
        l = len(full)
        i = index + 1
        while i < l:
            entry = full[i]
            if self._is_visible(entry):
                return entry
            i += 1
        return None

    def _is_visible(self, entry):
        return 'hidden' in entry and not entry['hidden']


def invalidate_content(sender, instance, **kwargs):
    course = instance
    while hasattr(course, 'course_instance'):
        course = course.course_instance
    CachedContent.invalidate(course)


# Automatically invalidate cached course content when edited.
post_save.connect(invalidate_content, sender=CourseInstance)
post_save.connect(invalidate_content, sender=CourseModule)
post_save.connect(invalidate_content, sender=LearningObject)
post_delete.connect(invalidate_content, sender=CourseInstance)
post_delete.connect(invalidate_content, sender=CourseModule)
post_delete.connect(invalidate_content, sender=LearningObject)
