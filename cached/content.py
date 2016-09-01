from django.db.models.signals import post_save, post_delete
from django.utils import timezone

from course.models import CourseInstance, CourseModule, LearningObjectCategory
from exercise.models import LearningObject, BaseExercise
from .abstract import CachedAbstract


class NoSuchContent(Exception):
    pass


class ContentMixin(object):

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

    def categories(self):
        categories = list(self.data['categories'].values())
        categories.sort(key=lambda entry: entry['name'])
        return categories

    def modules(self):
        full = self.full_hierarchy()
        return [e for e in full if e['type'] == 'module']

    def exercises(self):
        full = self.full_hierarchy()
        return [e for e in full if e['type'] == 'exercise']

    def begin(self):
        for e in self.full_hierarchy():
            if e['type'] == 'exercise' and self.is_listed(e):
                return e

    def total(self):
        return self.data['total']

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
            if self.is_listed(entry):
                return entry
            i -= 1
        return None

    def _next(self, full, index):
        l = len(full)
        i = index + 1
        while i < l:
            entry = full[i]
            if self.is_listed(entry):
                return entry
            i += 1
        return None

    @classmethod
    def is_visible(cls, entry):
        t = entry['type']
        if t == 'exercise':
            return (
                entry['module_status'] != CourseModule.STATUS.HIDDEN
                and not entry['status'] in (
                    LearningObject.STATUS.HIDDEN,
                    LearningObject.STATUS.ENROLLMENT,
                    LearningObject.STATUS.ENROLLMENT_EXTERNAL,
                )
            )
        if t == 'module':
            return entry['status'] != CourseModule.STATUS.HIDDEN
        if t == 'category':
            return entry['status'] != LearningObjectCategory.STATUS.HIDDEN
        return False

    @classmethod
    def is_listed(cls, entry):
        if not cls.is_visible(entry):
            return False
        t = entry['type']
        if t == 'exercise':
            return (
                entry['module_status'] != CourseModule.STATUS.UNLISTED
                and entry['status'] != LearningObject.STATUS.UNLISTED
            )
        if t == 'module':
            return entry['status'] != CourseModule.STATUS.UNLISTED
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


class CachedContent(ContentMixin, CachedAbstract):
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
        categories = {}
        total = {
            'min_group_size': 100000,
            'max_group_size': 1,
        }

        def recursion(module, objects, parents, parent_id):
            """ Recursively travels exercises hierarchy """
            children = [o for o in objects if o.parent_id == parent_id]
            if children:
                flat[-1]['has_children'] = True
                for o in children:
                    o._parents = parents + [o]
                    category = o.category
                    flat.append({
                        'has_children': False,
                        'close_levels': [],
                        'type': 'exercise',
                        'category': str(category),
                        'category_id': category.id,
                        'module_id': module.id,
                        'module_status': module.status,
                        'id': o.id,
                        'order': o.order,
                        'status': o.status,
                        'name': str(o),
                        'link': o.get_absolute_url(),
                        'submissions_link': o.get_submission_list_url(),
                        'parent': (exercise_index[parent_id]
                            if not parent_id is None
                            else module_index[module.id]),
                        'breadcrumb': [exercise_index[o.id] for o in parents],
                        'opening_time': module.opening_time,
                        'closing_time': module.closing_time,
                        'is_empty': o.is_empty(),
                        'points_to_pass': 0,
                        'max_submissions': 0,
                        'max_points': 0,
                    })
                    if o.status == LearningObject.STATUS.UNLISTED:
                        if parents:
                            flat[-1]['parent_link'] = parents[-1].get_absolute_url()
                    exercise_index[o.id] = len(flat) - 1
                    paths[module.id][o.get_path()] = o.id
                    if not category.id in categories:
                        categories[category.id] = {
                            'type': 'category',
                            'id': category.id,
                            'status': category.status,
                            'name': str(category),
                            'points_to_pass': category.points_to_pass,
                        }
                    recursion(module, objects, o._parents, o.id)
                flat[-1]['close_levels'].append('m' if parent_id is None else 'e')

        # Collect each module.
        for module in instance.course_modules.all():
            flat.append({
                'has_children': False,
                'close_levels': [],
                'type': 'module',
                'id': module.id,
                'order': module.order,
                'status': module.status,
                'name': str(module),
                'introduction': module.introduction,
                'link': module.get_absolute_url(),
                'opening_time': module.opening_time,
                'closing_time': module.closing_time,
                'late_allowed': module.late_submissions_allowed,
                'late_time': module.late_submission_deadline,
                'late_percent': module.get_late_submission_point_worth(),
                'points_to_pass': module.points_to_pass,
            })
            module_index[module.id] = len(flat) - 1
            paths[module.id] = {}
            recursion(module, list(module.learning_objects.all()), [], None)

        # Augment submission parameters.
        for exercise in BaseExercise.objects\
              .filter(course_module__course_instance=instance):
            entry = flat[exercise_index[exercise.id]]
            entry.update({
                'submittable': True,
                'points_to_pass': exercise.points_to_pass,
                'max_submissions': exercise.max_submissions,
                'max_points': exercise.max_points,
            })
            if exercise.max_group_size > total['max_group_size']:
                total['max_group_size'] = exercise.max_group_size
            if exercise.max_group_size > 1 and exercise.min_group_size < total['min_group_size']:
                total['min_group_size'] = exercise.min_group_size
        if total['min_group_size'] > total['max_group_size']:
            total['min_group_size'] = 1

        return {
            'created': timezone.now(),
            'module_index': module_index,
            'exercise_index': exercise_index,
            'paths': paths,
            'flat': flat,
            'categories': categories,
            'total': total,
        }


def invalidate_content(sender, instance, **kwargs):
    course = instance
    while hasattr(course, 'course_instance'):
        course = course.course_instance
    CachedContent.invalidate(course)


# Automatically invalidate cached course content when edited.
post_save.connect(invalidate_content, sender=CourseInstance)
post_delete.connect(invalidate_content, sender=CourseInstance)
post_save.connect(invalidate_content, sender=CourseModule)
post_delete.connect(invalidate_content, sender=CourseModule)
post_save.connect(invalidate_content, sender=LearningObject)
post_delete.connect(invalidate_content, sender=LearningObject)
post_save.connect(invalidate_content, sender=LearningObjectCategory)
post_delete.connect(invalidate_content, sender=LearningObjectCategory)
