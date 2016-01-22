from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from lib.viewbase import BaseTemplateView
from userprofile.viewbase import ACCESS, UserProfileMixin
from .models import Course, CourseInstance, CourseModule


class CourseMixin(UserProfileMixin):
    course_kw = "course"

    def get_resource_objects(self):
        super().get_resource_objects()
        self.course = get_object_or_404(
            Course,
            url=self._get_kwarg(self.course_kw)
        )
        self.is_teacher = self.course.is_teacher(self.request.user)
        self.note("course", "is_teacher")

    def access_control(self):
        super().access_control()
        if self.access_mode >= ACCESS.TEACHER:
            if not self.is_teacher:
                messages.error(self.request,
                    _("Only course teachers shall pass."))
                raise PermissionDenied()


class CourseBaseView(CourseMixin, BaseTemplateView):
    pass


class CourseInstanceMixin(CourseMixin):
    instance_kw = "instance"

    def get_resource_objects(self):
        super().get_resource_objects()
        self.instance = get_object_or_404(
            CourseInstance,
            url=self._get_kwarg(self.instance_kw),
            course=self.course
        )
        self.is_assistant = self.instance.is_assistant(self.request.user)
        self.is_course_staff = self.is_teacher or self.is_assistant
        self.note("instance", "is_assistant", "is_course_staff")

        # Loosen the access mode if instance is public.
        if self.instance.view_access == 0 and self.access_mode == ACCESS.STUDENT:
            self.access_mode = ACCESS.ANONYMOUS

    def access_control(self):
        super().access_control()
        if self.access_mode >= ACCESS.ASSISTANT:
            if not self.is_course_staff:
                messages.error(self.request,
                    _("Only course staff shall pass."))
                raise PermissionDenied()
        else:
            if not self.instance.is_visible_to(self.request.user):
                messages.error(self.request,
                    _("The resource is not currently visible."))
                raise PermissionDenied()

            # View access.
            if self.instance.view_access == 2 and not self.profile.is_external:
                messages.error(self.request, _("This course is only for external students."))
                raise PermissionDenied()
            if self.instance.view_access > 2 and self.profile.is_external:
                messages.error(self.request, _("This course is only for internal students."))
                raise PermissionDenied()


class CourseInstanceBaseView(CourseInstanceMixin, BaseTemplateView):
    pass


class CourseModuleMixin(CourseInstanceMixin):
    module_kw = "module"

    def get_resource_objects(self):
        super().get_resource_objects()
        self.module = get_object_or_404(
            CourseModule,
            url=self._get_kwarg(self.module_kw),
            course_instance=self.instance
        )
        self.note("module")

    def access_control(self):
        super().access_control()
        if not self.is_course_staff:
            if self.module.status == CourseModule.STATUS_HIDDEN:
                raise Http404()
            if not self.module.is_after_open():
                messages.error(self.request,
                    _("The module will open for submissions at {date}").format(
                        date=self.module.opening_time))
                raise PermissionDenied()


class CourseModuleBaseView(CourseModuleMixin, BaseTemplateView):
    pass
