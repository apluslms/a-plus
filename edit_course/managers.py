from typing import Any

from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from exercise.models import LearningObject, CourseChapter, \
    BaseExercise, LTIExercise, StaticExercise, ExerciseWithAttachment
from course.models import LearningObjectCategory, CourseModule
from .exercise_forms import CourseChapterForm, BaseExerciseForm, \
    LTIExerciseForm, ExerciseWithAttachmentForm, StaticExerciseForm, \
    ExerciseCollectionExerciseForm
from .course_forms import LearningObjectCategoryForm, CourseModuleForm
from exercise.exercisecollection_models import ExerciseCollection

class ModelManager:
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

    def new_object(self, instance, parent_id, type): # pylint: disable=unused-argument redefined-builtin
        return self.object_class(course_instance=instance) # pylint: disable=not-callable

    def get_form_class(self, _obj):
        return self.form_class

    def can_delete(self, _obj):
        return True


class ExerciseContainerMixin:

    def can_delete(self, obj: Any) -> bool:
        return not obj.learning_objects.exists()


class CategoryManager(ExerciseContainerMixin, ModelManager):
    object_class = LearningObjectCategory
    form_class = LearningObjectCategoryForm
    name = _('CATEGORY_lowercase')


class ModuleManager(ExerciseContainerMixin, ModelManager):
    object_class = CourseModule
    form_class = CourseModuleForm
    name = _('MODULE')

    def new_object(self, instance, parent_id, type): # pylint: disable=redefined-builtin
        return self.object_class(
            course_instance=instance,
            order=(instance.course_modules.count() + 1)
        )


class ExerciseManager(ModelManager):
    object_class = LearningObject
    instance_field = "course_module__course_instance"
    name = _('LEARNING_OBJECT')


    def new_object(self, instance, parent_id, type): # pylint: disable=redefined-builtin
        CLASSES = {
            None: BaseExercise,
            "lti": LTIExercise,
            "chapter": CourseChapter,
            "static": StaticExercise,
            "attachment": ExerciseWithAttachment,
        }
        if type not in CLASSES:
            raise Http404()
        object_class = CLASSES[type]

        module = get_object_or_404(
            CourseModule,
            id=parent_id,
            course_instance=instance
        )
        kwargs = {
            "course_module": module,
            "order": module.learning_objects.filter(parent__isnull=True).count() + 1,
        }
        first_category = instance.categories.first()
        if first_category:
            kwargs["category"] = first_category
        return object_class(**kwargs)

    def get_form_class(self, obj):
        FORMS = {
            CourseChapter: CourseChapterForm,
            BaseExercise: BaseExerciseForm,
            LTIExercise: LTIExerciseForm,
            StaticExercise: StaticExerciseForm,
            ExerciseWithAttachment: ExerciseWithAttachmentForm,
            ExerciseCollection: ExerciseCollectionExerciseForm,

        }
        if obj.__class__ not in FORMS:
            raise TypeError("No form known for the object type: %s", # pylint: disable=raising-format-tuple
                obj.__class__)
        return FORMS[obj.__class__]
