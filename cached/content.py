from django.core.cache import cache
from django.db.models.signals import post_save, post_delete

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
        flat = []

        for module in instance.course_modules.all():
            flat.append({
                'type': 'module',
                'hidden': not module.status in (CourseModule.STATUS.READY, CourseModule.STATUS.MAINTENANCE),
                'maintenance': module.status == CourseModule.STATUS.MAINTENANCE,
                'name': str(module),
                'link': module.get_absolute_url(),
                'model': module,
            })
            module_index[module.id] = len(flat) - 1
            self._generate_recursion(
                flat,
                exercise_index,
                list(module.learning_objects.all()),
                [],
                None
            )

        return {
            'module_index': module_index,
            'exercise_index': exercise_index,
            'flat': flat,
        }

    def _generate_recursion(self, flat, index, objects, parents, parent_id):
        children = [o for o in objects if o.parent_id == parent_id]
        if children:
            flat.append({
                'type': 'level_open',
            })
            for o in children:
                flat.append({
                    'type': 'exercise',
                    'hidden': not o.status in (LearningObject.STATUS.READY, LearningObject.STATUS.MAINTENANCE),
                    'maintenance': o.status == LearningObject.STATUS.MAINTENANCE,
                    'name': o.name,
                    'link': None,
                    'model': o,
                })
                index[o.id] = len(flat) - 1
                self._generate_recursion(flat, index, objects, parents + [o], o.id)
            flat.append({
                'type': 'level_close',
            })

    def full_hierarchy(self):
        return self.data['flat']

    def module_hierarchy(self, module):
        i = self._index_model(module) + 1
        full = self.full_hierarchy()
        l = len(full)
        module = []
        while i < l and full[i]['type'] != 'module':
            module.append(full[i])
            i += 1
        return module

    def siblings(self, model):
        i = self._index_model(model)
        return self._previous(i), self._next(i)

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
        full = self.full_hierarchy()
        i = index - 1
        while i >= 0:
            entry = full[i]
            if self._is_visible(entry):
                return entry
            i -= 1
        return None

    def _next(self, index):
        full = self.full_hierarchy()
        l = len(full)
        i = index + 1
        while i < len(full):
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
