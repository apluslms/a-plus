from typing import Any, TYPE_CHECKING, cast

from django.contrib.auth.models import User
from django.db.models.query import QuerySet
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from authorization.permissions import (
    ACCESS,
    Permission,
    MessageMixin,
    ObjectVisibleBasePermission,
    FilterBackend,
)
from exercise.cache.points import CachedPoints
from userprofile.models import UserProfile
from .models import (
    CourseModule,
    CourseInstance,
)

if TYPE_CHECKING:
    from course.viewbase import CourseInstanceBaseMixin, CourseModuleMixin


class CourseVisiblePermission(ObjectVisibleBasePermission[CourseInstance]):
    message = _('COURSE_VISIBILITY_PERMISSION_DENIED_MSG')
    model = CourseInstance
    obj_var = 'instance'

    def is_object_visible(
            self,
            request: HttpRequest,
            view: 'CourseInstanceBaseMixin',
            course: CourseInstance,
            ) -> bool:
        """
        Find out if CourseInstance is visible to user
        We expect that AccessModePermission is checked first

         - Always visible to course staff
         - Always hidden if not open (visible_to_students)
         - Always visible if public
         - If not public:
           - Require authentication
           - If view_access == enrolled -> visible if student of the course
           - If enrollment audience external, user should be external
           - If enrollment audience internal, user should be internal
        """
        # NOTE: course is actually course instance

        # Course is always visible to staff members
        if view.is_course_staff:
            return True

        # Course is not visible if it's hidden
        if not course.visible_to_students:
            self.error_msg(_('COURSE_VISIBILITY_ERROR_NOT_VISIBLE'))
            return False

        user = cast(User, request.user)
        show_for = course.view_content_to
        VA = course.VIEW_ACCESS

        # FIXME: we probably should test if access_mode is ANONYMOUS (public), but that
        # would break api permissiosn (requires get_access_mode)
        if show_for != VA.PUBLIC:
            if not user.is_authenticated:
                self.error_msg(_('COURSE_VISIBILITY_ERROR_NOT_PUBLIC'))
                return False

            # Allow enrolled students. This is important when students that
            # do not belong to the enrollment audience are manually enrolled
            # in the course.
            # Avoid querying the database again if we can read
            # CourseInstanceBaseMixin.is_student.
            try:
                is_student = view.is_student
            except AttributeError:
                is_student = course.is_student(user)
            if is_student:
                return True

            # Handle enroll views separately
            if view.get_access_mode() == ACCESS.ENROLL:
                return self.enrollment_audience_check(request, course, user)

            if show_for == VA.ENROLLED:
                # Already checked above that the user has not enrolled.
                self.error_msg(_('ACCESS_ERROR_ONLY_ENROLLED_STUDENTS'))
                return False

            elif show_for == VA.ENROLLMENT_AUDIENCE:
                return self.enrollment_audience_check(request, course, user)

        return True

    def enrollment_audience_check(
            self,
            request: HttpRequest,
            course: CourseInstance,
            user: User,
            ) -> bool:
        audience = course.enrollment_audience
        external = user.userprofile.is_external
        EA = course.ENROLLMENT_AUDIENCE
        if audience == EA.INTERNAL_USERS and external:
            self.error_msg(_('COURSE_ENROLLMENT_AUDIENCE_ERROR_ONLY_INTERNAL'))
            return False
        elif audience == EA.EXTERNAL_USERS and not external:
            self.error_msg(_('COURSE_ENROLLMENT_AUDIENCE_ERROR_ONLY_EXTERNAL'))
            return False
        return True


class EnrollInfoVisiblePermission(ObjectVisibleBasePermission[CourseInstance]):
    message = _('COURSE_VISIBILITY_PERMISSION_DENIED_MSG')
    model = CourseInstance
    obj_var = 'instance'

    def is_object_visible(
            self,
            request: HttpRequest,
            view: 'CourseInstanceBaseMixin',
            course_instance: CourseInstance,
            ) -> bool:
        # Course is always visible to staff members
        if view.is_course_staff:
            return True

        # Course is not visible if it's hidden
        if not course_instance.visible_to_students:
            self.error_msg(_('COURSE_VISIBILITY_ERROR_NOT_VISIBLE'))
            return False

        # Only public courses may be browsed without logging in.
        if course_instance.view_content_to != course_instance.VIEW_ACCESS.PUBLIC \
                and not request.user.is_authenticated:
            self.error_msg(_('COURSE_VISIBILITY_ERROR_NOT_PUBLIC'))
            return False

        return True


class CourseModulePermission(MessageMixin, Permission):
    message = _('MODULE_PERMISSION_MSG_NOT_VISIBLE')

    def has_permission(self, request: HttpRequest, view: 'CourseModuleMixin') -> bool:
        if not view.is_course_staff:
            module = view.module
            return self.has_object_permission(request, view, module)
        return True

    def has_object_permission(
            self,
            request: HttpRequest,
            view: 'CourseModuleMixin',
            module: CourseModule,
            ) -> bool:

        if not isinstance(module, CourseModule):
            return True

        if module.status == CourseModule.STATUS.HIDDEN:
            return False

        if not module.is_after_open():
            # FIXME: use format from django settings
            self.error_msg(
                _('MODULE_PERMISSION_ERROR_NOT_OPEN_YET -- {date}'),
                format={'date': module.opening_time},
                delim=' ',
            )
            return False

        if module.requirements.count() > 0:
            points = CachedPoints(module.course_instance, request.user, view.content)
            return module.are_requirements_passed(points)
        return True


class OnlyCourseTeacherPermission(Permission):
    message = _('COURSE_PERMISSION_MSG_ONLY_TEACHER')

    def has_permission(self, request: HttpRequest, view: 'CourseInstanceBaseMixin') -> bool:
        return self.has_object_permission(request, view, view.instance)

    def has_object_permission(
            self,
            request: HttpRequest,
            view: 'CourseInstanceBaseMixin',
            obj: Any,
            ) -> bool:
        return view.is_teacher or request.user.is_superuser


class OnlyCourseStaffPermission(Permission):
    message = _('COURSE_PERMISSION_MSG_ONLY_COURSE_STAFF')

    def has_permission(self, request: HttpRequest, view: 'CourseInstanceBaseMixin') -> bool:
        return self.has_object_permission(request, view, view.instance)

    def has_object_permission(
            self,
            request: HttpRequest,
            view: 'CourseInstanceBaseMixin',
            obj: Any,
            ) -> bool:
        return view.is_course_staff or request.user.is_superuser


class IsCourseAdminOrUserObjIsSelf(OnlyCourseStaffPermission, FilterBackend):

    def has_object_permission(
            self,
            request: HttpRequest,
            view: 'CourseInstanceBaseMixin',
            obj: UserProfile,
            ) -> bool:
        if not isinstance(obj, UserProfile):
            return True

        user = request.user
        return user and (
            (user.id is not None and user.id == obj.user_id) or
            super().has_object_permission(request, view, obj)
        )

    def filter_queryset(
            self,
            request: HttpRequest,
            queryset: QuerySet[UserProfile],
            view: 'CourseInstanceBaseMixin',
            ) -> QuerySet[UserProfile]:
        user = request.user
        if (
            issubclass(queryset.model, UserProfile) and
            not view.is_course_staff and
            not user.is_superuser
        ):
            queryset = queryset.filter(user_id=user.id)
        return queryset


class OnlyEnrolledStudentOrCourseStaffPermission(Permission):
    message = _('COURSE_PERMISSION_MSG_ONLY_ENROLLED_STUDENTS_OR_COURSE_STAFF')

    def has_permission(self, request: HttpRequest, view: 'CourseInstanceBaseMixin') -> bool:
        return self.has_object_permission(request, view, None)

    def has_object_permission(
            self,
            request: HttpRequest,
            view: 'CourseInstanceBaseMixin',
            obj: Any,
            ) -> bool:
        try:
            return view.is_student or view.is_course_staff or request.user.is_superuser
        except AttributeError:
            return False

