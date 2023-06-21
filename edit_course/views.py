import urllib.parse

from aplus_auth.payload import Permission, Permissions
from aplus_auth.requests import post as aplus_post
from aplus_auth.requests import put as aplus_put
from django.conf import settings
from django.contrib import messages
from django.db import models, IntegrityError
from django.http.response import Http404
from django.utils.text import format_lazy, capfirst
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext_lazy as ngettext
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, \
    FormView

from lib.viewbase import (
    BaseViewMixin,
    BaseTemplateMixin,
    BaseTemplateView,
    BaseRedirectMixin,
    BaseRedirectView,
    BaseFormView,
)
from aplus.api import api_reverse
from authorization.permissions import ACCESS
from course.models import UserTag, UserTagging
from course.viewbase import CourseInstanceMixin
from exercise.cache.content import CachedContent
from exercise.cache.exercise import invalidate_instance
from exercise.cache.hierarchy import NoSuchContent
from exercise.models import LearningObject
from .course_forms import CourseInstanceForm, CourseIndexForm, \
    CourseContentForm, CloneInstanceForm, GitmanagerForm, UserTagForm, SelectUsersForm
from .managers import CategoryManager, ModuleManager, ExerciseManager
from .operations.batch import create_submissions
from .operations.configure import configure_from_url, get_build_log
from lib.logging import SecurityLog
from userprofile.models import UserProfile


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
        SecurityLog.logevent(self.request, "course-edit", "course: {}, teachers: {}, assistants: {}".format(
            self.get_course_instance_object().course,
            list(map(lambda x: str(x.user), form.instance.teachers.all())),
            list(map(lambda x: str(x.user), form.instance.assistants.all()))
        ))
        messages.success(self.request, _('SUCCESS_SAVING_CHANGES'))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _('FAILURE_SAVING_CHANGES'))
        return super().form_invalid(form)


class EditIndexView(EditInstanceView):
    template_name = "edit_course/edit_index.html"
    form_class = CourseIndexForm

    def get_success_url(self):
        return self.instance.get_url('course-index')


class EditContentView(EditInstanceView):
    template_name = "edit_course/edit_content.html"
    form_class = CourseContentForm

    def get_common_objects(self) -> None:
        self.modules = list(
            self.instance.course_modules.prefetch_related('learning_objects'),
        )
        for module in self.modules:
            learning_objects = {lobject.id: lobject for lobject in module.learning_objects.all()}
            module.flat_objects = []
            try:
                for entry in self.content.flat_module(module, enclosed=False):
                    if entry.type != 'level':
                        learning_object = learning_objects.get(entry.id)
                        if learning_object:
                            module.flat_objects.append(learning_object)
            except NoSuchContent:
                continue
        self.categories = self.instance.categories.annotate(
            count_lobjects=models.Count('learning_objects')
        )
        self.note('modules', 'categories')

    def get_success_url(self):
        return self.instance.get_url('course-edit')

    def form_valid(self, form):
        if self.request.POST.get('renumbermodule') is not None:
            for module in self.content.modules():
                self.renumber_recursion(module)
        elif self.request.POST.get('renumbercourse') is not None:
            n = 1
            for module in self.content.modules():
                nn = self.renumber_recursion(module, n)
                if module.status != 'hidden':
                    n = nn
        return super().form_valid(form)

    def renumber_recursion(self, parent, n=1):
        for entry in parent.children:
            model = LearningObject.objects.get(id=entry['id'])
            model.order = n
            model.save()
            self.renumber_recursion(entry)
            n += 1
        return n


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
        if self.model not in MANAGERS:
            raise Http404()
        self.manager = MANAGERS[self.model]()
        self.model_name = self.manager.name
        # FIXME: model is passed from kwargs in View.dispatch and from
        # BaseMixin/BaseTemplateMixin to template context. As the value is
        # same, this should break anything, but is still a problematic thing.
        # Should be fixed one day.
        self.note("model", "model_name")

    def get_success_url(self):
        return self.instance.get_edit_url()


class ModelEditView(ModelBaseMixin, BaseFormView):
    template_name = "edit_course/edit_model.html"
    parent_kw = "parent_id"
    type_kw = "type"

    def get_resource_objects(self) -> None:
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
            if not self.instance.categories.exists():
                messages.error(self.request,
                    _('ERROR_EXERCISE_CATEGORY_MUST_EXIST_BEFORE_CREATEING_EXERCISES'))
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
                format_lazy(
                    _('FAILURE_SAVING_MODEL_DUE_TO_ERROR -- {name}, {error}'),
                    name=self.model_name,
                    error=e,
                )
            )
            return super().form_invalid(form)
        messages.success(self.request,
            capfirst(format_lazy(
                _('SUCCESS_SAVING_MODEL -- {name}'),
                name=self.model_name,
            ))
        )
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request,
            format_lazy(
                _('FAILURE_SAVING_MODEL -- {name}'),
                name=self.model_name,
            )
        )
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
        if self.empty:
            self.object.delete()
        return self.redirect(self.get_success_url())


class UserTagMixin(CourseInstanceMixin, BaseTemplateMixin, BaseViewMixin):
    access_mode = ACCESS.TEACHER
    form_class = UserTagForm
    pk_url_kwarg = "tag_id"
    success_url_name = "course-tags"

    def get_success_url(self):
        return self.instance.get_url(self.success_url_name)

    def get_queryset(self):
        return self.instance.usertags.all()


class UserTagListView(UserTagMixin, ListView):
    template_name = "edit_course/usertag_list.html"

class UserTagAddView(UserTagMixin, CreateView):
    template_name = "edit_course/usertag_add.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if 'instance' not in kwargs or not kwargs['instance']:
            kwargs.update({'instance': self.form_class.get_base_object(self.instance)})
        return kwargs


class UserTagEditView(UserTagMixin, UpdateView):
    template_name = "edit_course/usertag_edit.html"

class UserTagDeleteView(UserTagMixin, DeleteView):
    template_name = "edit_course/usertag_delete.html"

class UserTaggingAddView(UserTagMixin, FormView):
    form_class = SelectUsersForm
    template_name = "edit_course/usertagging_add.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.instance
        return kwargs

    def form_valid(self, form):
        user_set = form.cleaned_data['user']
        tag_id = self.kwargs['tag_id']
        tag = UserTag.objects.get(pk=tag_id)

        for user in user_set:
            UserTagging.objects.set(user, tag)

        user_name = ', '.join([ user.user.username for user in user_set ])
        tag_name = tag.name
        messages.success(
            self.request,
            format_lazy(
                ngettext(
                    'TAGGED_USER_WITH_TAG -- {user_name}, {tag_name}',
                    'TAGGED_USERS_WITH_TAG -- {user_name}, {tag_name}',
                    user_set.count()
                ),
                user_name=user_name,
                tag_name=tag_name,
            )
        )

        return super().form_valid(form)


class BatchCreateSubmissionsView(CourseInstanceMixin, BaseTemplateView):
    access_mode = ACCESS.TEACHER
    template_name = "edit_course/batch_assess.html"

    def post(self, request, *args, **kwargs):
        errors = create_submissions(self.instance, self.profile,
            request.POST.get("submissions_json", "{}"))
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            messages.success(request, _('NEW_SUBMISSIONS_STORED'))
        return self.render_to_response(self.get_context_data())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        exercises_api_url = api_reverse("course-exercises-list", kwargs={'course_id': self.instance.id})
        context.update({'exercises_api_url': exercises_api_url})
        return context


class CloneInstanceView(CourseInstanceMixin, BaseFormView):
    access_mode = ACCESS.TEACHER
    template_name = "edit_course/clone_instance.html"
    form_class = CloneInstanceForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.instance
        return kwargs

    def form_valid(self, form):
        from .operations.clone import clone # pylint: disable=import-outside-toplevel
        new_instance = clone(
            cloner=UserProfile.get_by_request(self.request),
            instance=self.instance,
            url=form.cleaned_data['url'],
            name=form.cleaned_data['instance_name'],
            clone_teachers=form.cleaned_data['teachers'],
            clone_assistants=form.cleaned_data['assistants'],
            clone_usertags=form.cleaned_data['usertags'],
            clone_menuitems=form.cleaned_data['menuitems'],
            siskey=form.cleaned_data.get('sis'),
            sisenroll=form.cleaned_data.get('sis_enroll'),
        )

        if not all(
            [settings.GITMANAGER_URL, form.cleaned_data.get('git_origin'), form.cleaned_data.get('git_branch')]
        ):
            # Do not create a new entry in Git manager
            messages.success(self.request, _('COURSE_INSTANCE_CLONED'))
            return self.redirect(new_instance.get_url('course-details'))

        key = "{}_{}{}".format(self.course.code, form.cleaned_data['key_year'], form.cleaned_data['key_month'])

        data = {
            "key": key,
            "remote_id": new_instance.id,
            "update_automatically": form.cleaned_data['update_automatically'],
            "email_on_error": form.cleaned_data['email_on_error'],
            "git_origin": form.cleaned_data['git_origin'],
            "git_branch": form.cleaned_data['git_branch'],
        }

        permissions = Permissions()
        permissions.instances.add(Permission.WRITE, id=new_instance.id)
        gitmanager_url = urllib.parse.urljoin(settings.GITMANAGER_URL, f"api/gitmanager/{key}/")

        try:
            response = aplus_post(gitmanager_url, permissions=permissions, data=data)
            if response.status_code == 200:
                new_instance.configure_url = urllib.parse.urljoin(settings.GITMANAGER_URL, f"{key}/aplus-json")
                new_instance.save()
                gitmanager_hook_url = urllib.parse.urljoin(settings.GITMANAGER_URL, f"gitmanager/{key}/hook")
                response = aplus_post(gitmanager_hook_url, permissions=permissions, data={"key": key})
            if response.status_code != 200:
                messages.error(self.request, _('GITMANAGER_ERROR') + response.text)
        except Exception as e:
            messages.error(self.request, str(e))

        messages.success(self.request, _('COURSE_INSTANCE_CLONED'))
        messages.info(self.request, _('COURSE_INSTANCE_BUILD_DURATION_INFO'))
        messages.info(self.request, _('COURSE_INSTANCE_WEBHOOK_INFO'))
        return self.redirect(new_instance.get_url('course-details'))


class EditGitmanagerView(CourseInstanceMixin, BaseFormView):
    access_mode = ACCESS.TEACHER
    template_name = "edit_course/edit_gitmanager.html"
    form_class = GitmanagerForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.instance
        return kwargs

    def form_valid(self, form):
        data = {
            "key": form.cleaned_data['key'],
            "remote_id": form.cleaned_data['remote_id'],
            "update_automatically": form.cleaned_data['update_automatically'],
            "email_on_error": form.cleaned_data['email_on_error'],
            "git_origin": form.cleaned_data['git_origin'],
            "git_branch": form.cleaned_data['git_branch'],
            "update_hook": form.cleaned_data['update_hook'],
            "webhook_secret": form.cleaned_data['webhook_secret'],
        }

        permissions = Permissions()
        permissions.instances.add(Permission.WRITE, id=self.instance.id)
        gitmanager_url = urllib.parse.urljoin(settings.GITMANAGER_URL, f"api/gitmanager/id/{self.instance.id}")

        try:
            response = aplus_put(gitmanager_url, permissions=permissions, data=data)
            if response.status_code == 404:
                del data['webhook_secret']
                response = aplus_post(gitmanager_url, permissions=permissions, data=data)
            if response.status_code == 200:
                key = form.cleaned_data['key']
                self.instance.configure_url = urllib.parse.urljoin(settings.GITMANAGER_URL, f"{key}/aplus-json")
                self.instance.save()
                gitmanager_hook_url = urllib.parse.urljoin(settings.GITMANAGER_URL, f"gitmanager/{key}/hook")
                response = aplus_post(gitmanager_hook_url, permissions=permissions, data={"key": key})
                messages.success(self.request, _('GITMANAGER_UPDATED'))
            if response.status_code != 200:
                messages.error(self.request, _('GITMANAGER_ERROR') + response.text)
        except Exception as e:
            messages.error(self.request, str(e))

        return self.redirect(self.instance.get_url('gitmanager-details'))


class ConfigureContentView(CourseInstanceMixin, BaseRedirectView):
    access_mode = ACCESS.TEACHER

    def post(self, request, *args, **kwargs):
        if 'apply' in request.POST:
            self.configure(request)
        elif 'cache' in request.POST:
            self.clear_cache(request)
        elif 'reset' in request.POST:
            self.instance.delete_cached_config()
            self.configure(request)
        return self.redirect(self.instance.get_url('course-edit'))

    def configure(self, request):
        try:
            success, errors = configure_from_url(self.instance, request.POST.get('url'))
            if success:
                if errors:
                    messages.warning(request, _("CONFIGURED_WITH_WARNINGS"))
                    for error in errors:
                        messages.warning(request, error)
                else:
                    messages.success(request, _('COURSE_CONTENT_CONFIGURED'))
            elif errors:
                messages.error(request, _("CONFIGURED_WITH_ERRORS"))
                for error in errors:
                    messages.error(request, error)
            else:
                messages.error(request, _("CONFIGURE_FAILED"))
        except Exception as e:
            messages.error(request,
                format_lazy(
                    _('ERROR_SERVER_RETURNED_ERROR -- {error!s}'),
                    error=e,
                )
            )

    def clear_cache(self, request):
        invalidate_instance(self.instance)
        CachedContent.invalidate(self.instance)
        messages.success(request, _('EXERCISE_CACHES_CLEARED'))


class BuildLogView(CourseInstanceMixin, BaseTemplateView):
    access_mode = ACCESS.TEACHER
    template_name = "edit_course/build_log.html"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update(get_build_log(self.instance))
        return context
