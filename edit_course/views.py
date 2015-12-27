from django.contrib import messages
from django.db import IntegrityError
from django.http.response import Http404
from django.utils.translation import ugettext_lazy as _

from course.models import CourseInstance
from course.viewbase import CourseInstanceBaseView, CourseInstanceMixin
from lib.viewbase import BaseTemplateView, BaseRedirectMixin, BaseFormView, \
    BaseRedirectView
from userprofile.viewbase import ACCESS
from .course_forms import CourseInstanceForm, CourseIndexForm, \
    CourseContentForm, CloneInstanceForm
from .managers import CategoryManager, ModuleManager, ExerciseManager


class EditInstanceView(CourseInstanceMixin, BaseFormView):
    access_mode = ACCESS.TEACHER
    template_name = "edit_course/edit_instance.html"
    form_class = CourseInstanceForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.instance
        return kwargs

    def get_success_url(self):
        return self.instance.get_url('course-details')

    def form_valid(self, form):
        self.instance = form.save()
        messages.success(self.request, _("Changes were saved succesfully."))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("Failed to save changes."))
        return super().form_invalid(form)


class EditIndexView(EditInstanceView):
    template_name = "edit_course/edit_index.html"
    form_class = CourseIndexForm

    def get_success_url(self):
        return self.instance.get_url('course-index')


class EditContentView(EditInstanceView):
    template_name = "edit_course/edit_content.html"
    form_class = CourseContentForm

    def get_success_url(self):
        return self.instance.get_url('course-edit')

    def form_valid(self, form):
        if self.request.POST.get('renumbermodule') is not None:
            for module in self.instance.course_modules.all():
                module._children().renumber()
        elif self.request.POST.get('renumbercourse') is not None:
            n = 1
            for module in self.instance.course_modules.exclude(status='hidden'):
                n = module._children().renumber(n)
        return super().form_valid(form)


class ModelBaseMixin(CourseInstanceMixin):
    access_mode = ACCESS.TEACHER
    model_kw = "model"
    id_kw = "id"

    def get_resource_objects(self):
        super().get_resource_objects()
        MANAGERS = {
            "category": CategoryManager,
            "module": ModuleManager,
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

    def form_invalid(self, form):
        messages.error(self.request,
            _('Failed to save {name}').format(name=self.model_name))
        return super().form_invalid(form)


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
        from .operations.batch import create_submissions
        errors = create_submissions(self.instance, self.profile,
            request.POST.get("submissions_json", "{}"))
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            messages.success(request, _("New submissions stored."))
        return self.response()


class CloneInstanceView(CourseInstanceMixin, BaseFormView):
    access_mode = ACCESS.TEACHER
    template_name = "edit_course/clone_instance.html"
    form_class = CloneInstanceForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.instance
        return kwargs

    def form_valid(self, form):
        from .operations.clone import clone
        instance = clone(self.instance, form.cleaned_data['url'])
        messages.success(self.request, _("Course instance is now cloned."))
        return self.redirect(instance.get_url('course-details'))


class ConfigureContentView(CourseInstanceMixin, BaseRedirectView):
    access_mode = ACCESS.TEACHER

    def post(self, request, *args, **kwargs):
        self.handle()
        from .operations.configure import configure_content
        errors = configure_content(self.instance, request.POST.get('url'))
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            messages.success(request, _("Course content configured."))
        return self.redirect(self.instance.get_url('course-edit'))
