from __future__ import annotations
from typing import Any, Dict, List, Optional, Type, Union

from django.db.models.base import Model
from django.db.models.signals import post_save, post_delete
from django.utils import timezone

from course.models import CourseInstance, CourseModule, LearningObjectCategory
from lib.cache import CachedAbstract
from .basetypes import CachedDataBase, CategoryEntryBase, ExerciseEntryBase, ModuleEntryBase, TotalsBase
from .hierarchy import ContentMixin
from ..models import LearningObject, BaseExercise


Totals = TotalsBase
CategoryEntry = CategoryEntryBase
# This is a class because a type alias with ForwardRefs cannot be pickled, and exists purely for typing
class ExerciseEntry(ExerciseEntryBase["ModuleEntry", "ExerciseEntry"]): ...
ModuleEntry = ModuleEntryBase[ExerciseEntry]
CachedContentData = CachedDataBase[ModuleEntry, ExerciseEntry, CategoryEntry, Totals]


class CachedContent(CachedAbstract[CachedContentData], ContentMixin[ModuleEntry, ExerciseEntry, CategoryEntry, Totals]):
    """ Course content hierarchy for template presentations """
    KEY_PREFIX = 'content'

    def __init__(self, course_instance: CourseInstance) -> None:
        self.instance = course_instance
        super().__init__(course_instance)
    # pylint: disable-next=arguments-differ too-many-locals
    def _generate_data(self, instance: CourseInstance, data: Optional[CachedContentData] = None) -> CachedContentData:
        """ Returns object that is cached into self.data """
        module_index: Dict[int, ModuleEntry] = {}
        exercise_index: Dict[int, ExerciseEntry] = {}
        paths: Dict[int, Dict[str, int]] = {}
        modules: List[ModuleEntry] = []
        categories: Dict[int, CategoryEntry] = {}
        total = Totals()

        def recursion(
                module: ModuleEntry,
                objects: List[LearningObject],
                parents: List[LearningObject],
                container: List[ExerciseEntry],
                ) -> None:
            """ Recursively travels exercises hierarchy """
            parent_id = parents[-1].id if parents else None
            children = [o for o in objects if o.parent_id == parent_id]
            j = 0
            for o in children:
                o._parents = parents + [o]
                category = o.category
                entry = ExerciseEntry(
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
                    categories[category.id] = CategoryEntry(
                        id = category.id,
                        status = category.status,
                        name = str(category),
                        points_to_pass = category.points_to_pass,
                    )
                recursion(module, objects, o._parents, entry.children)
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
            'learning_objects',
        ):
            entry = ModuleEntry(
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
            all_children = list(module.learning_objects.all())
            recursion(entry, all_children, [], entry.children)
            i += 1

        # Augment submittable exercise parameters.
        def add_to(target: Union[ModuleEntry, CategoryEntry, Totals], exercise: BaseExercise) -> None:
            target.exercise_count += 1
            target.max_points += exercise.max_points
            self._add_by_difficulty(
                target.max_points_by_difficulty,
                exercise.difficulty,
                exercise.max_points
            )
        for exercise in BaseExercise.objects\
              .filter(course_module__course_instance=instance):
            try:
                entry = exercise_index[exercise.id]
            except KeyError:
                self.dirty = True
                continue

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

        return CachedContentData(
            created = timezone.now(),
            module_index = module_index,
            exercise_index = exercise_index,
            paths = paths,
            modules = modules,
            categories = categories,
            total = total,
        )


def invalidate_content(
        sender: Type[Model], # pylint: disable=unused-argument
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
