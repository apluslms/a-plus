import json
import logging
from django.contrib import messages
from django.db import IntegrityError
from django.http.response import Http404
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from course.models import CourseInstance
from course.viewbase import CourseInstanceBaseView, CourseInstanceMixin
from exercise.models import BaseExercise
from lib.helpers import extract_form_errors
from lib.viewbase import BaseTemplateView, BaseRedirectMixin, BaseFormView, \
    BaseRedirectView
from userprofile.viewbase import ACCESS
from .course_forms import CourseInstanceForm, CourseContentForm
from .managers import CategoryManager, ModuleManager, ChapterManager, \
    ExerciseManager
from .submission_forms import BatchSubmissionCreateAndReviewForm
from exercise.submission_models import Submission


logger = logging.getLogger('aplus.edit_course')


class EditContentView(CourseInstanceMixin, BaseFormView):
    access_mode = ACCESS.TEACHER
    template_name = "edit_course/edit_content.html"
    form_class = CourseContentForm

    def get_from_kwargs(self):
        kwargs = super().get_from_kwargs()
        kwargs["instance"] = self.instance
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, _("Changes saved."))
        return self.response()


class EditInstanceView(CourseInstanceMixin, BaseFormView):
    access_mode = ACCESS.TEACHER
    template_name = "edit_course/edit_instance.html"
    form_class = CourseInstanceForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.instance
        return kwargs

    def form_valid(self, form):
        self.instance = form.save()
        messages.success(self.request, _("Changes were saved succesfully."))
        return self.redirect(self.instance.get_url('course-details'))


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
    template_name = "edit_course/edit_model.html"
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
            if self.instance.categories.count() == 0:
                messages.error(self.request,
                    _("At least one exercise category must be created before "
                      "creating exercises."))
        self.note("object")

    def get_form_class(self):
        return self.manager.get_form_class(self.object)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.object
        return kwargs

    def form_valid(self, form):
        try:
            self.object = form.save()
        except IntegrityError as e:
            messages.error(self.request,
                _('Save failed: {error}').format(error=repr(e)))
            return super().form_invalid(form)
        messages.success(self.request,
            _('The {name} was saved successfully.').format(
                name=self.model_name))
        return super().form_valid(form)


class ModelDeleteView(ModelBaseMixin, BaseRedirectMixin, BaseTemplateView):
    template_name = "edit_course/remove_model.html"

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


class BatchCreateSubmissionsView(CourseInstanceMixin, BaseTemplateView):
    access_mode = ACCESS.TEACHER
    template_name = "edit_course/batch_assess.html"

    def post(self, request, *args, **kwargs):
        self.handle()
        self.error = False
        try:
            submissions_json = json.loads(
                request.POST.get("submissions_json", "{}"))
        except Exception as e:
            logger.exception(
                "Failed to parse submission batch JSON from user: %s",
                request.user.username)
            self.set_error(
                _("Failed to parse the JSON: {error}"),
                error=str(e))
        if not self.error and not "objects" in submissions_json:
            self.set_error(_('Missing JSON field: objects'))

        validated_forms = []
        if not self.error:
            count = 0
            for submission_json in submissions_json["objects"]:
                count += 1
                if not "exercise_id" in submission_json:
                    self.set_error(
                        _('Missing field "exercise_id" in object {count:d}.'),
                        count=count)
                    continue

                exercise = BaseExercise.objects.filter(
                    id=submission_json["exercise_id"],
                    course_module__course_instance=self.instance).first()
                if not exercise:
                    self.set_error(
                        _('Unknown exercise_id {id} in object {count:d}.'),
                        count=count,
                        id=submission_json["exercise_id"])
                    continue

                # Use form to parse and validate object data.
                form = BatchSubmissionCreateAndReviewForm(submission_json,
                    exercise=exercise)
                if form.is_valid():
                    validated_forms.append(form)
                else:
                    self.set_error(
                        _('Invalid fields in object {count:d}: {error}'),
                        count=count,
                        error="\n".join(extract_form_errors(form)))

        if not self.error:
            for form in validated_forms:
                sub = Submission.objects.create(exercise=form.exercise)
                sub.submitters = form.cleaned_data.get("students") \
                    or form.cleaned_data.get("students_by_student_id")
                sub.feedback = form.cleaned_data.get("feedback")
                sub.set_points(form.cleaned_data.get("points"),
                    sub.exercise.max_points, no_penalties=True)
                sub.submission_time = form.cleaned_data.get("submission_time")
                sub.grading_time = timezone.now()
                sub.grader = form.cleaned_data.get("grader") or self.profile
                sub.set_ready()
                sub.save()
            messages.success(request, _("New submissions stored."))

        return self.response()

    def set_error(self, text, **kwargs):
        messages.error(self.request, text.format(**kwargs))
        self.error = True


class CloneInstanceView(CourseInstanceMixin, BaseRedirectView):

    def post(self, request, *args, **kwargs):
        self.handle()
        url = self.request.POST.get("new_url", "").strip()
        if not url:
            messages.error(request, _("Url was missing."))
        elif CourseInstance.objects.filter(course=self.course, url=url)\
            .exists():
            messages.error(request,
                _("Url '{}' is already taken.").format(url))
        else:
            assistants = list(self.instance.assistants.all())
            categories = list(self.instance.categories.all())
            modules = list(self.instance.course_modules.all())
            self.instance.id = None
            self.instance.visible_to_students = False
            self.instance.url = url
            self.instance.save()

            self.instance.assistants.add(*assistants)

            category_map = {}
            for category in categories:
                old_id = category.id
                category.id = None
                category.course_instance = self.instance
                category.save()
                category_map[old_id] = category

            for module in modules:
                chapters = list(module.chapters.all())
                exercises = list(a.as_leaf_class()
                    for a in module.learning_objects.all())
                module.id = None
                module.course_instance = self.instance
                module.save()

                for chapter in chapters:
                    chapter.id = None
                    chapter.course_module = module
                    chapter.save()

                for exercise in exercises:
                    exercise.id = None
                    exercise.learningobject_ptr_id = None
                    exercise.modelwithinheritance_ptr_id = None
                    exercise.course_module = module
                    exercise.category = category_map[exercise.category.id]
                    exercise.save()
            messages.success(request, _("Course instance is now cloned."))

        return self.redirect(self.instance.get_url('course-details'))
