from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import translation
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import get_language

from authorization.permissions import ACCESS
from exercise.cache.content import CachedContent
from lib.viewbase import BaseTemplateView
from userprofile.viewbase import UserProfileMixin
from .cache.students import CachedStudents
from .permissions import (
    CourseVisiblePermission,
    CourseModulePermission,
)
from .models import Course, CourseInstance, CourseModule, UserTagging


class CourseMixin(UserProfileMixin):
    course_kw = "course_slug"

    def get_resource_objects(self):
        super().get_resource_objects()
        self.course = get_object_or_404(
            Course,
            url=self._get_kwarg(self.course_kw)
        )
        self.is_teacher = self.course.is_teacher(self.request.user)
        self.note("course", "is_teacher")


class CourseBaseView(CourseMixin, BaseTemplateView):
    pass


class CourseInstanceBaseMixin(object):
    course_kw = CourseMixin.course_kw
    instance_kw = "instance_slug"
    course_permission_classes = (
        CourseVisiblePermission,
    )

    def get_permissions(self):
        perms = super().get_permissions()
        perms.extend((Perm() for Perm in self.course_permission_classes))
        return perms

    # get_course_instance_object

    def get_resource_objects(self):
        super().get_resource_objects()
        user = self.request.user
        instance = self.get_course_instance_object()
        if instance is not None:
            self.instance = instance
            self.course = self.instance.course
            self.content = CachedContent(self.instance)
            self.is_student = self.instance.is_student(user)
            self.is_assistant = self.instance.is_assistant(user)
            self.is_teacher = self.course.is_teacher(user)
            self.is_course_staff = self.is_teacher or self.is_assistant
            def get_taggings():
                return [tag
                        for student in CachedStudents(instance).students()
                        if student['user_id'] == user.id
                        for tag in student['tag_slugs']]
            self.get_taggings = get_taggings

            self.note(
                "course", "instance", "content", "is_student", "is_assistant",
                "is_teacher", "is_course_staff", "get_taggings",
            )

            # Apply course instance language.
            if self.instance.language:
                lang = self.instance.language
                if lang.startswith("|"):
                    active = get_language()
                    if "|" + active + "|" in lang:
                        translation.activate(active)
                    else:
                        fallback = lang[1:lang.find("|", 1)]
                        translation.activate(fallback)
                else:
                    translation.activate(lang)

    def get_access_mode(self):
        access_mode = super().get_access_mode()

        if hasattr(self, 'instance'):
            # Loosen the access mode if instance is public
            show_for = self.instance.view_content_to
            is_public = show_for == CourseInstance.VIEW_ACCESS.PUBLIC
            access_mode_student = access_mode in (ACCESS.STUDENT, ACCESS.ENROLL)
            if is_public and access_mode_student:
                access_mode = ACCESS.ANONYMOUS

        return access_mode


class CourseInstanceMixin(CourseInstanceBaseMixin, UserProfileMixin):
    def get_course_instance_object(self):
        return get_object_or_404(
            CourseInstance,
            url=self.kwargs[self.instance_kw],
            course__url=self.kwargs[self.course_kw],
        )


class CourseInstanceBaseView(CourseInstanceMixin, BaseTemplateView):
    pass


class EnrollableViewMixin(CourseInstanceMixin):
    access_mode = ACCESS.ENROLL

    def get_common_objects(self):
        self.enrolled = self.is_student
        self.enrollable = (
            self.profile
            and self.instance.is_enrollable(self.profile.user)
        )
        self.note('enrolled', 'enrollable')


class CourseModuleBaseMixin(object):
    module_kw = "module_slug"
    module_permissions_classes = (
        CourseModulePermission,
    )

    def get_permissions(self):
        perms = super().get_permissions()
        perms.extend((Perm() for Perm in self.module_permissions_classes))
        return perms

    # get_course_module_object

    def get_resource_objects(self):
        super().get_resource_objects()
        self.module = self.get_course_module_object()
        self.note("module")


class CourseModuleMixin(CourseModuleBaseMixin, CourseInstanceMixin):
    def get_course_module_object(self):
        return get_object_or_404(
            CourseModule,
            url=self.kwargs[self.module_kw],
            course_instance=self.instance
        )


class CourseModuleBaseView(CourseModuleMixin, BaseTemplateView):
    pass
