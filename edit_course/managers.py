from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from exercise.models import LearningObject, BaseExercise, StaticExercise, \
    ExerciseWithAttachment
from course.models import LearningObjectCategory, CourseModule, \
    CourseChapter
from .exercise_forms import BaseExerciseForm, ExerciseWithAttachmentForm, \
    StaticExerciseForm
from .course_forms import LearningObjectCategoryForm, CourseModuleForm, \
    CourseChapterForm


class ModelManager(object):
    object_class = None
    instance_field = "course_instance"
    form_class = None
    name = None

    def get_object(self, instance, object_id):
        fields = {
            "id": object_id,
            self.instance_field: instance,
        }
        return get_object_or_404(self.object_class, **fields)

    def new_object(self, instance, parent_id, type):
        return self.object_class(course_instance=instance)

    def get_form_class(self, obj):
        return self.form_class

    def can_delete(self, obj):
        return True


class ExerciseContainerMixin(object):

    def can_delete(self, obj):
        return obj.learning_objects.count() == 0


class CategoryManager(ExerciseContainerMixin, ModelManager):
    object_class = LearningObjectCategory
    form_class = LearningObjectCategoryForm
    name = _("category")


class ModuleManager(ExerciseContainerMixin, ModelManager):
    object_class = CourseModule
    form_class = CourseModuleForm
    name = _("module")

    def new_object(self, instance, parent_id, type):
        return self.object_class(
            course_instance=instance,
            order=(instance.course_modules.count() + 1)
        )


class ChapterManager(ModelManager):
    object_class = CourseChapter
    instance_field = "course_module__course_instance"
    form_class = CourseChapterForm
    name = _("chapter")

    def new_object(self, instance, parent_id, type):
        module = get_object_or_404(
            CourseModule,
            id=parent_id,
            course_instance=instance
        )
        return self.object_class(
            course_module=module,
            order=(module.chapters.count() + 1)
        )


class ExerciseManager(ModelManager):
    object_class = LearningObject
    instance_field = "course_module__course_instance"
    name = _("exercise")

    def get_object(self, instance, object_id):
        obj = super().get_object(instance, object_id)
        return obj.as_leaf_class()

    def new_object(self, instance, parent_id, type):
        CLASSES = {
            None: BaseExercise,
            "static": StaticExercise,
            "attachment": ExerciseWithAttachment,
        }
        if not type in CLASSES:
            raise Http404()
        object_class = CLASSES[type]

        module = get_object_or_404(
            CourseModule,
            id=parent_id,
            course_instance=instance
        )
        kwargs = {
            "course_module": module,
            "order": module.learning_objects.count() + 1,
        }
        first_category = instance.categories.first()
        if first_category:
            kwargs["category"] = first_category
        return object_class(**kwargs)

    def get_form_class(self, obj):
        FORMS = {
            BaseExercise: BaseExerciseForm,
            StaticExercise: StaticExerciseForm,
            ExerciseWithAttachment: ExerciseWithAttachmentForm,
        }
        if obj.__class__ not in FORMS:
            raise TypeError("No form known for the exercise type: %s",
                obj.__class__)
        return FORMS[obj.__class__]
