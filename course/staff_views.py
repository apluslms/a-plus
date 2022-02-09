import json
from typing import Any, Dict, List

from django.contrib import messages
from django.db import models
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext_lazy as ngettext

from authorization.permissions import ACCESS
from lib.helpers import settings_text
from lib.viewbase import BaseFormView, BaseTemplateView, BaseRedirectMixin
from userprofile.models import UserProfile
from .cache.students import CachedStudent
from .forms import EnrollStudentsForm, GroupEditForm
from .models import (
    Enrollment,
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
        # Maps enum name (e.g. "ACTIVE") to string (e.g. "Active").
        self.enrollment_statuses = {
            k: str(Enrollment.ENROLLMENT_STATUS[getattr(Enrollment.ENROLLMENT_STATUS, k)])
            for k in Enrollment.ENROLLMENT_STATUS.keys()
        }
        self.enrollment_statuses_json = json.dumps(self.enrollment_statuses)
        self.participants = json.dumps(self._get_students_with_tags())
        self.internal_user_label = settings_text('INTERNAL_USER_LABEL')
        self.external_user_label = settings_text('EXTERNAL_USER_LABEL')
        self.note(
            'participants', 'tags',
            'enrollment_statuses', 'enrollment_statuses_json',
            'internal_user_label', 'external_user_label',
        )

    def _get_students_with_tags(self) -> List[Dict[str, Any]]:
        ci = self.instance
        fake = '10' * 32
        link = (reverse('user-results',
                         kwargs={'user_id': fake, **ci.get_url_kwargs()})
                .replace(fake, r'%s'))
        tags = {t.slug: t for t in self.tags}
        # Maps enum value (e.g. 1) to name (e.g. "ACTIVE").
        statuses = {
            getattr(Enrollment.ENROLLMENT_STATUS, k): k
            for k in Enrollment.ENROLLMENT_STATUS.keys()
        }

        participants = ci.all_students.prefetch_tags(ci)
        data = []
        for participant in participants:
            user_id = participant.user.id
            user_tags = CachedStudent(ci, participant.user).data
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
                'enrollment_status': statuses[participant.enrollment_status],
            })
        return data


class GroupsView(CourseInstanceBaseView):
    access_mode = ACCESS.ASSISTANT
    template_name = "course/staff/groups.html"

    def get_common_objects(self) -> None:
        super().get_common_objects()
        self.groups = list(
            self.instance.groups.prefetch_related(
                models.Prefetch('members', UserProfile.objects.prefetch_tags(self.instance)),
            )
        )
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

    def get_resource_objects(self) -> None:
        super().get_resource_objects()
        self.group = get_object_or_404(
            StudentGroup.objects.prefetch_related(
                models.Prefetch('members', UserProfile.objects.prefetch_tags(self.instance))
            ),
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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.instance
        return kwargs

    def form_valid(self, form):
        if (self.instance.sis_id and form.cleaned_data["sis"]):
            count = self.instance.enroll_from_sis()
            if count >= 0:
                messages.info(
                    self.request,
                    format_lazy(
                        ngettext(
                            'STUDENT_ENROLLED_FROM_SIS -- {count}',
                            'STUDENTS_ENROLLED_FROM_SIS -- {count}',
                            count
                        ),
                        count=count,
                    )
                )
            else:
                messages.warning(self.request, _('COULD_NOT_ACCESS_SIS'))

        failed_already_enrolled = []
        failed_course_staff = []
        for profile in form.cleaned_data["user_profiles"]:
            if self.instance.is_course_staff(profile.user):
                # Course staff cannot be demoted into students by enrolling
                # them via this view.
                failed_course_staff.append(profile)
                continue
            if not self.instance.enroll_student(profile.user):
                # If the selected student was already enrolled,
                # we can show a warning here.
                failed_already_enrolled.append(profile)
        if failed_already_enrolled:
            messages.warning(
                self.request,
                format_lazy(
                    _('ENROLLMENTS_FAILED_WARNING_USERS_ALREADY_ENROLLED -- {users}'),
                    users='; '.join([profile.name_with_student_id for profile in failed_already_enrolled]),
                ),
            )
        if failed_course_staff:
            messages.warning(
                self.request,
                format_lazy(
                    _('ENROLLMENTS_FAILED_WARNING_COURSE_STAFF -- {users}'),
                    users='; '.join([profile.user.get_full_name() for profile in failed_course_staff]),
                ),
            )
        return super().form_valid(form)

    def get_success_url(self):
        return self.instance.get_url('participants')
