from __future__ import annotations

from course.models import CourseInstance
from .basetypes import CachedDataBase, CategoryEntryBase, LearningObjectEntryBase, ModuleEntryBase, TotalsBase
from .hierarchy import ContentMixin


Totals = TotalsBase
CategoryContent = CategoryEntryBase
# This is a class because a type alias with ForwardRefs cannot be pickled (i.e. cached)
class LearningObjectContent(LearningObjectEntryBase["ModuleContent", "LearningObjectContent"]): ...


ModuleContent = ModuleEntryBase[LearningObjectContent]
InstanceContent = CachedDataBase[ModuleContent, LearningObjectContent, CategoryContent, Totals]


class CachedContent(ContentMixin[ModuleContent, LearningObjectContent, CategoryContent, Totals]):
    """ Course content hierarchy for template presentations """
    instance: CourseInstance
    data: InstanceContent

    def __init__(self, instance: CourseInstance, prefetch_children: bool = True):
        self.instance = instance
        self.data = InstanceContent.get(instance, prefetch_children=prefetch_children)

    @classmethod
    def invalidate(cls, instance: CourseInstance):
        InstanceContent.invalidate(instance)
        for module in instance.course_modules.prefetch_related("learning_objects").all():
            ModuleEntryBase.invalidate(module)
            for exercise in module.learning_objects.all():
                LearningObjectEntryBase.invalidate(exercise)
