from __future__ import annotations
from typing import Any, ClassVar, Dict, List, Type, Union

from django.db.models.base import Model
from django.db.models.signals import post_save, post_delete

from course.models import CourseInstance, CourseModule, LearningObjectCategory
from lib.cache.cached import CacheBase
from .basetypes import CachedDataBase, CategoryEntryBase, ExerciseEntryBase, ModuleEntryBase, TotalsBase
from .hierarchy import ContentMixin
from ..models import BaseExercise, LearningObject


Totals = TotalsBase
CategoryEntry = CategoryEntryBase
# This is a class because a type alias with ForwardRefs cannot be pickled (i.e. cached)
class ExerciseEntry(ExerciseEntryBase["ModuleEntry", "ExerciseEntry"]): ...
ModuleEntry = ModuleEntryBase[ExerciseEntry]
CachedContentData = CachedDataBase[ModuleEntry, ExerciseEntry, CategoryEntry, Totals]


class CachedContent(ContentMixin[ModuleEntry, ExerciseEntry, CategoryEntry, Totals]):
    """ Course content hierarchy for template presentations """
    instance: CourseInstance
    data: CachedContentData

    def __init__(self, instance: CourseInstance):
        self.instance = instance
        self.data = CachedContentData.get_for_models(instance)

    @classmethod
    def invalidate(cls, instance: CourseInstance):
        CachedContentData.invalidate(instance)
        for module in instance.course_modules.prefetch_related("learning_objects").all():
            ModuleEntryBase.invalidate(module)
            for exercise in module.learning_objects.all():
                ExerciseEntryBase.invalidate(exercise)


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
