from __future__ import annotations

from course.models import CourseInstance
from .basetypes import CachedDataBase, CategoryEntryBase, ExerciseEntryBase, ModuleEntryBase, TotalsBase
from .hierarchy import ContentMixin


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
        self.data = CachedContentData.get(instance)

    @classmethod
    def invalidate(cls, instance: CourseInstance):
        CachedContentData.invalidate(instance)
        for module in instance.course_modules.prefetch_related("learning_objects").all():
            ModuleEntryBase.invalidate(module)
            for exercise in module.learning_objects.all():
                ExerciseEntryBase.invalidate(exercise)
