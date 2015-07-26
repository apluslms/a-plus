from django.contrib import messages
from django.http.response import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from lib.viewbase import BaseTemplateView, BaseRedirectMixin, BaseFormView
from exercise.exercise_forms import BaseExerciseForm, \
    ExerciseWithAttachmentForm
from exercise.models import LearningObject, BaseExercise, StaticExercise, \
    ExerciseWithAttachment
from course.forms import CourseModuleForm, CourseChapterForm, \
    LearningObjectCategoryForm
from course.models import CourseModule, CourseChapter, LearningObjectCategory
from course.viewbase import CourseInstanceBaseView, CourseInstanceMixin
from userprofile.viewbase import ACCESS


class EditCourseView(CourseInstanceBaseView):
    access_mode = ACCESS.TEACHER
    template_name = "course/teacher/course_instance.html"


class ModelBaseMixin(CourseInstanceMixin):
    access_mode = ACCESS.TEACHER
    model_kw = "model"
    id_kw = "id"

    def get_resource_objects(self):
        super().get_resource_objects()
        MANAGERS = {
            "category": CategoryManager,
            "module": ModuleManager,
            "chapter": ChapterManager,
            "exercise": ExerciseManager,
        }
        self.model = self._get_kwarg(self.model_kw)
        if not self.model in MANAGERS:
            raise Http404()
        self.manager = MANAGERS[self.model]()
        self.model_name = self.manager.name
        self.note("model", "model_name")

    def get_success_url(self):
        return self.instance.get_edit_url()


class ModelEditView(ModelBaseMixin, BaseFormView):
    template_name = "course/teacher/edit_model.html"
    parent_kw = "parent_id"
    type_kw = "type"

    def get_resource_objects(self):
        super().get_resource_objects()
        object_id = self._get_kwarg(self.id_kw, default=None)
        if object_id:
            self.object = self.manager.get_object(
                self.instance,
                object_id
            )
        else:
            self.object = self.manager.new_object(
                self.instance,
                self._get_kwarg(self.parent_kw, default=None),
                self._get_kwarg(self.type_kw, default=None)
            )
        self.note("object")

    def get_form_class(self):
        return self.manager.get_form_class(self.object)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.object
        return kwargs

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request,
            _('The {name} was saved successfully.').format(
                name=self.model_name))
        return super().form_valid(form)


class ModelDeleteView(ModelBaseMixin, BaseRedirectMixin, BaseTemplateView):
    template_name = "course/teacher/remove_model.html"

    def get_resource_objects(self):
        super().get_resource_objects()
        self.object = self.manager.get_object(
            self.instance,
            self._get_kwarg(self.id_kw)
        )
        self.note("object")

    def get_common_objects(self):
        super().get_common_objects()
        self.empty = self.manager.can_delete(self.object)
        self.note("object", "empty")

    def post(self, request, *args, **kwargs):
        self.handle()
        if self.empty:
            self.object.delete()
        return self.redirect(self.get_success_url())


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
        return object_class(
            course_module=module,
            order=(module.learning_objects.count() + 1)
        )

    def get_form_class(self, obj):
        FORMS = {
            BaseExercise: BaseExerciseForm,
            StaticExercise: BaseExerciseForm,
            ExerciseWithAttachment: ExerciseWithAttachmentForm,
        }
        if obj.__class__ not in FORMS:
            raise TypeError("No form known for the exercise type: %s",
                obj.__class__)
        return FORMS[obj.__class__]
