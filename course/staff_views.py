import json
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from authorization.permissions import ACCESS
from lib.helpers import settings_text
from lib.viewbase import BaseFormView, BaseTemplateView, BaseRedirectMixin
from .cache.students import CachedStudents
from .forms import GroupEditForm
from .models import StudentGroup
from .viewbase import CourseInstanceBaseView, CourseInstanceMixin


class ParticipantsView(CourseInstanceBaseView):
    access_mode = ACCESS.ASSISTANT
    template_name = "course/staff/participants.html"

    def get_common_objects(self):
        super().get_common_objects()
        self.participants = json.dumps(CachedStudents(self.instance).students())
        self.tags = list(self.instance.usertags.all())
        self.internal_user_label = settings_text('INTERNAL_USER_LABEL')
        self.external_user_label = settings_text('EXTERNAL_USER_LABEL')
        self.note(
            'participants', 'tags',
            'internal_user_label', 'external_user_label',
        )


class GroupsView(CourseInstanceBaseView):
    access_mode = ACCESS.ASSISTANT
    template_name = "course/staff/groups.html"

    def get_common_objects(self):
        super().get_common_objects()
        self.groups = list(self.instance.groups.all())
        self.note('groups')


class GroupsEditView(CourseInstanceMixin, BaseFormView):
    access_mode = ACCESS.ASSISTANT
    form_class = GroupEditForm
    group_kw = "group_id"
    template_name = "course/staff/group_edit.html"

    def get_resource_objects(self):
        super().get_resource_objects()
        gid = self._get_kwarg(self.group_kw, default=None)
        if gid:
            self.group = get_object_or_404(StudentGroup,
                course_instance=self.instance,
                id=gid,
            )
        else:
            self.group = StudentGroup(course_instance=self.instance)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.group
        return kwargs

    def get_success_url(self):
        return self.instance.get_url('groups-list')

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _("Changes were saved succesfully."))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("Failed to save changes."))
        return super().form_invalid(form)


class GroupsDeleteView(CourseInstanceMixin, BaseRedirectMixin, BaseTemplateView):
    access_mode = ACCESS.ASSISTANT
    group_kw = "group_id"
    template_name = "course/staff/group_delete.html"

    def get_resource_objects(self):
        super().get_resource_objects()
        self.group = get_object_or_404(StudentGroup,
            course_instance=self.instance,
            id=self._get_kwarg(self.group_kw),
        )
        self.note('group')

    def post(self, request, *args, **kwargs):
        self.group.delete()
        return self.redirect(self.instance.get_url('groups-list'))
