from django.http import Http404
from django.utils.translation import ugettext_lazy as _

from userprofile.models import UserProfile
from authorization.permissions import (
    ACCESS,
    Permission,
    MessageMixin,
    ObjectVisibleBasePermission,
    FilterBackend,
)
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
            self.error_msg(request, _("The resource is not currently visible."))
            return False

        user = request.user
        show_for = course.view_content_to
        VA = course.VIEW_ACCESS

        # FIXME: we probably should test if access_mode is ANONYMOUS (public), but that
        # would break api permissiosn (requires get_access_mode)
        if show_for != VA.PUBLIC:
            if not user.is_authenticated():
                self.error_msg(request, _("This course is not open for public"))
                return False

            if show_for == VA.ENROLLED:
                if not course.is_student(user):
                    self.error_msg(request, _("Only enrolled students shall pass."))
                    return False

            elif show_for == VA.ENROLLMENT_AUDIENCE:
                audience = course.enrollment_audience
                external = user.userprofile.is_external # FIXME: change user to userprofile
                EA = course.ENROLLMENT_AUDIENCE
                if audience == EA.INTERNAL_USERS and external:
                    self.error_msg(request, _("This course is only for internal students."))
                    return False
                elif audience == EA.EXTERNAL_USERS and not external:
                    self.error_msg(request, _("This course is only for external students."))
                    return False

        return True


class CourseModulePermission(MessageMixin, Permission):
    message = _("Permission denied by course module visibility")

    def has_permission(self, request, view):
        if not view.is_course_staff:
            module = view.module
            return self.has_object_permission(request, view, module)
        return True

    def has_object_permission(self, request, view, module):
        if not isinstance(module, CourseModule):
            return True

        if module.status == CourseModule.STATUS_HIDDEN:
            # FIXME: should probably just show error message and return False
            raise Http404("Course module not found")
        if not module.is_after_open():
            self.error_msg(request,
                _("The module will open for submissions at {date}").format(
                    date=module.opening_time))
            return False
        return True


class OnlyCourseTeacherPermission(Permission):
    message = _("Only course staff is allowed")

    def has_permission(self, request, view):
        return self.has_object_permission(request, view, view.instance)

    def has_object_permission(self, request, view, obj):
        user = request.user
        return (
            user.is_staff or
            user.is_superuser or
            view.is_teacher
        )


class IsCourseAdminOrUserItselfFilter(FilterBackend):
    def filter_queryset(self, request, queryset, view):
        user = request.user
        is_super = user.is_staff or user.is_superuser
        is_staff = view.is_course_staff
        if issubclass(queryset.model, UserProfile) and not is_super and not is_staff:
            queryset = queryset.filter(user_id=user.id)
        return queryset
