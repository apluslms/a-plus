from django.http import Http404
from django.utils.translation import ugettext_lazy as _

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


class CourseVisiblePermission(ObjectVisibleBasePermission):
    message = _("Permission denied by course visibility")
    model = CourseInstance
    obj_var = 'instance'

    def is_object_visible(self, request, view, course):
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
            self.error_msg(_("The resource is not currently visible."))
            return False

        user = request.user
        show_for = course.view_content_to
        VA = course.VIEW_ACCESS

        # FIXME: we probably should test if access_mode is ANONYMOUS (public), but that
        # would break api permissiosn (requires get_access_mode)
        if show_for != VA.PUBLIC:
            if not user.is_authenticated():
                self.error_msg(_("This course is not open for public."))
                return False

            # Handle enroll views separately
            if view.get_access_mode() == ACCESS.ENROLL:
                return self.enrollment_audience_check(request, course, user)

            if show_for == VA.ENROLLED:
                if not course.is_student(user):
                    self.error_msg(_("Only enrolled students shall pass."))
                    return False

            elif show_for == VA.ENROLLMENT_AUDIENCE:
                return self.enrollment_audience_check(request, course, user)

        return True

    def enrollment_audience_check(self, request, course, user):
        audience = course.enrollment_audience
        external = user.userprofile.is_external
        EA = course.ENROLLMENT_AUDIENCE
        if audience == EA.INTERNAL_USERS and external:
            self.error_msg(_("This course is only for internal students."))
            return False
        elif audience == EA.EXTERNAL_USERS and not external:
            self.error_msg(_("This course is only for external students."))
            return False
        return True


class EnrollInfoVisiblePermission(ObjectVisibleBasePermission):
    message = _("Permission denied by course visibility")
    model = CourseInstance
    obj_var = 'instance'

    def is_object_visible(self, request, view, course_instance):
        # Course is always visible to staff members
        if view.is_course_staff:
            return True

        # Course is not visible if it's hidden
        if not course_instance.visible_to_students:
            self.error_msg(_("The resource is not currently visible."))
            return False

        # Only public courses may be browsed without logging in.
        if course_instance.view_content_to != course_instance.VIEW_ACCESS.PUBLIC \
                and not request.user.is_authenticated:
            self.error_msg(_("This course is not open for public."))
            return False

        return True


class CourseModulePermission(MessageMixin, Permission):
    message = _("The module is not currently visible")

    def has_permission(self, request, view):
        if not view.is_course_staff:
            module = view.module
            return self.has_object_permission(request, view, module)
        return True

    def has_object_permission(self, request, view, module):
        if not isinstance(module, CourseModule):
            return True

        if module.status == CourseModule.STATUS.HIDDEN:
            return False

        if not module.is_after_open():
            # FIXME: use format from django settings
            self.error_msg(
                _("The module will open for submissions at {date}."),
                format={'date': module.opening_time},
                delim=' ',
            )
            return False

        if module.requirements.count() > 0:
            points = CachedPoints(module.course_instance, request.user, view.content)
            return module.are_requirements_passed(points)
        return True


class OnlyCourseTeacherPermission(Permission):
    message = _("Only course teacher is allowed")

    def has_permission(self, request, view):
        return self.has_object_permission(request, view, view.instance)

    def has_object_permission(self, request, view, obj):
        return view.is_teacher or request.user.is_superuser


class OnlyCourseStaffPermission(Permission):
    message = _("Only course staff is allowed")

    def has_permission(self, request, view):
        return self.has_object_permission(request, view, view.instance)

    def has_object_permission(self, request, view, obj):
        return view.is_course_staff or request.user.is_superuser


class IsCourseAdminOrUserObjIsSelf(OnlyCourseStaffPermission, FilterBackend):

    def has_object_permission(self, request, view, obj):
        if not isinstance(obj, UserProfile):
            return True

        user = request.user
        return user and (
            (user.id is not None and user.id == obj.user_id) or
            super().has_object_permission(request, view, obj)
        )

    def filter_queryset(self, request, queryset, view):
        user = request.user
        if (
            issubclass(queryset.model, UserProfile) and
            not view.is_course_staff and
            not user.is_superuser
        ):
            queryset = queryset.filter(user_id=user.id)
        return queryset
