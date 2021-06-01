import json
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from authorization.permissions import ACCESS
from lib.helpers import settings_text
from lib.viewbase import BaseFormView, BaseTemplateView, BaseRedirectMixin
from .cache.students import CachedStudent
from .forms import EnrollStudentsForm, GroupEditForm
from .models import (
    USERTAG_EXTERNAL,
    USERTAG_INTERNAL,
    StudentGroup,
)
from .viewbase import CourseInstanceBaseView, CourseInstanceMixin


class ParticipantsView(CourseInstanceBaseView):
    access_mode = ACCESS.ASSISTANT
    template_name = "course/staff/participants.html"

    def get_common_objects(self):
        super().get_common_objects()
        self.tags = [USERTAG_INTERNAL, USERTAG_EXTERNAL]
        self.tags.extend(self.instance.usertags.all())
        self.participants = json.dumps(self._get_students_with_tags())
        self.internal_user_label = settings_text('INTERNAL_USER_LABEL')
        self.external_user_label = settings_text('EXTERNAL_USER_LABEL')
        self.note(
            'participants', 'tags',
            'internal_user_label', 'external_user_label',
        )

    def _get_students_with_tags(self):
        ci = self.instance
        fake = '10' * 32
        link = (reverse('user-results',
                         kwargs={'user_id': fake, **ci.get_url_kwargs()})
                .replace(fake, r'%s'))
        tags = {t.slug: t for t in self.tags}

        participants = ci.students.all()
        data = []
        for participant in participants:
            user_id = participant.user.id
            user_tags = CachedStudent(ci, user_id).data
            user_tags_html = ' '.join(tags[slug].html_label for slug in user_tags['tag_slugs'] if slug in tags)
            data.append({
                'id': participant.student_id or '',
                'user_id': user_id,
                'last_name': participant.user.last_name or '',
                'first_name': participant.user.first_name or '',
                'username': participant.user.username,
                'email': participant.user.email or '',
                'external': participant.is_external,
                'link': link % (user_id,),
                **user_tags,
                'tags': user_tags_html,
            })
        return data


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
        messages.success(self.request, _('SUCCESS_SAVING_CHANGES'))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _('FAILURE_SAVING_CHANGES'))
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


class EnrollStudentsView(CourseInstanceMixin, BaseFormView):
    access_mode = ACCESS.TEACHER
    form_class = EnrollStudentsForm
    template_name = "course/staff/enroll_students.html"

    def form_valid(self, form):
        failed_enrollments = []
        for profile in form.cleaned_data["user_profiles"]:
            if not self.instance.enroll_student(profile.user):
                # If the selected student was already enrolled,
                # we can show a warning here.
                failed_enrollments.append(profile)
        if failed_enrollments:
            messages.warning(
                self.request,
                _('ENROLLMENTS_FAILED_WARNING_USERS_ALREADY_ENROLLED -- {users}').format(
                    users='; '.join([profile.name_with_student_id for profile in failed_enrollments]),
                ),
            )
        return super().form_valid(form)

    def get_success_url(self):
        return self.instance.get_url('participants')
