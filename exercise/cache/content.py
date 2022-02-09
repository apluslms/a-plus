from typing import Any, Dict, List, Optional, Type, Union

from django.db.models import Prefetch
from django.db.models.base import Model
from django.db.models.signals import post_save, post_delete
from django.utils import timezone

from course.models import CourseInstance, CourseModule, LearningObjectCategory
from lib.cache import CachedAbstract
from ..models import LearningObject, BaseExercise
from .hierarchy import ContentMixin


class CachedContent(ContentMixin, CachedAbstract):
    """ Course content hierarchy for template presentations """
    KEY_PREFIX = 'content'

    def __init__(self, course_instance: CourseInstance) -> None:
        self.instance = course_instance
        super().__init__(course_instance)

    def _generate_data(self, instance: CourseInstance, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """ Returns object that is cached into self.data """
        module_index = {}
        exercise_index = {}
        paths = {}
        modules = []
        categories = {}
        total = {
            'exercise_count': 0,
            'max_points': 0,
            'max_points_by_difficulty': {},
            'min_group_size': 100000,
            'max_group_size': 1,
        }

        def recursion(
                module: Dict[str, Any],
                objects: List[LearningObject],
                parents: List[LearningObject],
                indexes: List[int],
                container: List[Dict[str, Any]]
                ) -> None:
            """ Recursively travels exercises hierarchy """
            select = parents[-1].id if parents else None
            children = [o for o in objects if o.parent_id == select]
            j = 0
            for o in children:
                o._parents = parents + [o]
                category = o.category
                entry = {
                    'type': 'exercise',
                    'category': str(category),
                    'category_id': category.id,
                    'category_status': category.status,
                    'confirm_the_level': category.confirm_the_level,
                    'module_id': module['id'],
                    'module_status': module['status'],
                    'id': o.id,
                    'order': o.order,
                    'status': o.status,
                    'name': str(o),
                    'number': module['number'] + '.' + o.number(),
                    'link': o.get_display_url(),
                    'submittable': False,
                    'submissions_link': o.get_submission_list_url(),
                    'requirements': module['requirements'],
                    'opening_time': module['opening_time'],
                    'reading_opening_time': module['reading_opening_time'],
                    'closing_time': module['closing_time'],
                    'late_allowed': module['late_allowed'],
                    'late_time': module['late_time'],
                    'late_percent': module['late_percent'],
                    'is_empty': o.is_empty(),
                    'points_to_pass': 0,
                    'difficulty': '',
                    'max_submissions': 0,
                    'max_points': 0,
                    'allow_assistant_viewing': False,
                    'children': [],
                }
                container.append(entry)
                idx = indexes + [j]
                exercise_index[o.id] = idx
                paths[module['id']][o.get_path()] = o.id
                if not category.id in categories:
                    categories[category.id] = {
                        'type': 'category',
                        'id': category.id,
                        'status': category.status,
                        'name': str(category),
                        'points_to_pass': category.points_to_pass,
                        'exercise_count': 0,
                        'max_points': 0,
                        'max_points_by_difficulty': {},
                    }
                recursion(module, objects, o._parents, idx, entry['children'])
                j += 1

        # Collect each module.
        i = 0
        for module in instance.course_modules.prefetch_related(
            'requirements',
            'requirements__threshold__passed_modules',
            'requirements__threshold__passed_categories',
            'requirements__threshold__passed_exercises',
            'requirements__threshold__passed_exercises__parent',
            'requirements__threshold__points',
            Prefetch('learning_objects', LearningObject.objects.all()),
        ):
            entry = {
                'type': 'module',
                'id': module.id,
                'order': module.order,
                'status': module.status,
                'name': str(module),
                'number': str(module.order),
                'introduction': module.introduction,
                'link': module.get_absolute_url(),
                'requirements': [str(r) for r in module.requirements.all()],
                'opening_time': module.opening_time,
                'reading_opening_time': module.reading_opening_time,
                'closing_time': module.closing_time,
                'late_allowed': module.late_submissions_allowed,
                'late_time': module.late_submission_deadline,
                'late_percent': module.get_late_submission_point_worth(),
                'points_to_pass': module.points_to_pass,
                'exercise_count': 0,
                'max_points': 0,
                'max_points_by_difficulty': {},
                'children': [],
            }
            modules.append(entry)
            idx = [i]
            module_index[module.id] = idx
            paths[module.id] = {}
            all_children = list(module.learning_objects.all())
            recursion(entry, all_children, [], idx, entry['children'])
            i += 1

        # Augment submittable exercise parameters.
        def add_to(target: Dict[str, Any], exercise: BaseExercise) -> None:
            target['exercise_count'] += 1
            target['max_points'] += exercise.max_points
            self._add_by_difficulty(
                target['max_points_by_difficulty'],
                exercise.difficulty,
                exercise.max_points
            )
        for exercise in BaseExercise.objects\
              .filter(course_module__course_instance=instance):
            try:
                tree = self._by_idx(modules, exercise_index[exercise.id])
            except KeyError:
                self.dirty = True
                continue
            tree[-1].update({
                'submittable': True,
                'points_to_pass': exercise.points_to_pass,
                'difficulty': exercise.difficulty,
                'max_submissions': exercise.max_submissions,
                'max_points': exercise.max_points,
                'allow_assistant_viewing': exercise.allow_assistant_viewing,
            })

            if tree[-1]['confirm_the_level']:
                parent = tree[-2]
                parent['unconfirmed'] = True
                for entry in parent['children']:
                    entry['unconfirmed'] = True
            else:
                add_to(tree[0], exercise)
                add_to(categories[exercise.category.id], exercise)
                add_to(total, exercise)

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
            'modules': modules,
            'categories': categories,
            'total': total,
        }


def invalidate_content(
        sender: Type[Model],
        instance: Union[CourseInstance, CourseModule, LearningObject, LearningObjectCategory],
        **kwargs: Any,
        ) -> None:
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
