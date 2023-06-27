from typing import Any, Type

from aplus_auth.payload import Payload, Permission as AccessPermission
from django.http.request import HttpRequest
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from lib.helpers import settings_text
from authorization.permissions import (
    ACCESS,
    Permission,
    MessageMixin,
    ObjectVisibleBasePermission,
    FilterBackend,
)
from exercise.cache.points import CachedPoints
from exercise.models import BaseExercise, LearningObject
from exercise.submission_models import Submission
from userprofile.models import GraderUser, UserProfile
from .models import (
    Course,
    CourseModule,
    CourseInstance,
)


class JWTObjectPermission(Permission):
    obj_key: str
    obj_type: Type[Any]
    access_key: str
    access_type: AccessPermission
    id_key: str = "id"

    def get_obj(self, request, view):
        return getattr(view, self.obj_key)

    def has_object_in_permissions(self, request, view, obj): # pylint: disable=unused-argument
        return request.auth.permissions.has(self.access_key, self.access_type, **{self.id_key: obj.id})

    def has_permission(self, request, view):
        return self.has_object_permission(request, view, self.get_obj(request, view))

    def has_object_permission(self, request, view, obj):
        if not hasattr(request, "auth") or not isinstance(request.auth, Payload):
            return False
        if not isinstance(obj, self.obj_type):
            return True
        return self.has_object_in_permissions(request, view, obj)

class JWTCoursePermission(JWTObjectPermission):
    obj_key = "course"
    obj_type = Course
    access_key = "courses"

class JWTCourseWritePermission(JWTCoursePermission):
    message = _("NO_JWT_COURSE_PERMISSION")
    access_type = AccessPermission.WRITE

class JWTCourseReadPermission(JWTCoursePermission):
    message = _("NO_JWT_COURSE_PERMISSION")
    access_type = AccessPermission.READ

class JWTInstancePermission(JWTObjectPermission):
    obj_key = "instance"
    obj_type = CourseInstance
    access_key = "instances"

class JWTInstanceWritePermission(JWTInstancePermission):
    message = _("NO_JWT_INSTANCE_PERMISSION")
    access_type = AccessPermission.WRITE

class JWTInstanceReadPermission(JWTInstancePermission):
    message = _("NO_JWT_INSTANCE_PERMISSION")
    access_type = AccessPermission.READ

class JWTExercisePermission(JWTObjectPermission):
    obj_key = "exercise"
    obj_type = BaseExercise
    access_key = "exercises"

class JWTExerciseWritePermission(JWTExercisePermission):
    message = _("NO_JWT_EXERCISE_PERMISSION")
    access_type = AccessPermission.WRITE

class JWTExerciseReadPermission(JWTExercisePermission):
    message = _("NO_JWT_EXERCISE_PERMISSION")
    access_type = AccessPermission.READ

class JWTSubmissionPermission(JWTObjectPermission):
    obj_key = "submission"
    obj_type = Submission
    access_key = "submissions"

class JWTSubmissionReadPermission(JWTSubmissionPermission):
    message = _("NO_JWT_SUBMISSION_PERMISSION")
    access_type = AccessPermission.READ

class JWTSubmissionWritePermission(JWTSubmissionPermission):
    message = _("NO_JWT_SUBMISSION_PERMISSION")
    access_type = AccessPermission.WRITE

class JWTSubmissionCreatePermission(JWTObjectPermission):
    message = _("NO_JWT_SUBMISSION_PERMISSION")
    obj_key = "exercise"
    obj_type = BaseExercise
    access_key = "submissions"
    access_type = AccessPermission.CREATE
    id_key: str = "exercise_id"


class CourseVisiblePermissionBase(ObjectVisibleBasePermission):
    message = _('COURSE_VISIBILITY_PERMISSION_DENIED_MSG')
    model = CourseInstance
    obj_var = 'instance'

    def is_object_visible(self, request, view, course): # pylint: disable=arguments-renamed
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

        if isinstance(request.user, GraderUser):
            return False

        # Course is always visible to staff members
        if view.is_course_staff:
            return True

        # Course is not visible if it's hidden
        if not course.visible_to_students:
            self.error_msg(_('COURSE_VISIBILITY_ERROR_NOT_VISIBLE'))
            return False

        user = request.user
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

            if show_for == VA.ENROLLMENT_AUDIENCE:
                return self.enrollment_audience_check(request, course, user)

        return True

    def enrollment_audience_check(self, request, course, user):
        audience = course.enrollment_audience
        external = user.userprofile.is_external
        EA = course.ENROLLMENT_AUDIENCE
        institution_name = settings_text('BRAND_INSTITUTION_NAME')
        if audience == EA.INTERNAL_USERS and external:
            self.error_msg(
                format_lazy(
                    _('COURSE_ENROLLMENT_AUDIENCE_ERROR_ONLY_INTERNAL -- {institution}'),
                    institution=institution_name,
                )
            )
            return False
        if audience == EA.EXTERNAL_USERS and not external:
            self.error_msg(
                format_lazy(
                    _('COURSE_ENROLLMENT_AUDIENCE_ERROR_ONLY_EXTERNAL -- {institution}'),
                    institution=institution_name,
                )
            )
            return False
        return True


CourseVisiblePermission = CourseVisiblePermissionBase | JWTCourseReadPermission


class EnrollInfoVisiblePermission(ObjectVisibleBasePermission):
    message = _('COURSE_VISIBILITY_PERMISSION_DENIED_MSG')
    model = CourseInstance
    obj_var = 'instance'

    def is_object_visible(self, request, view, course_instance): # pylint: disable=arguments-renamed
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


class CourseModulePermissionBase(MessageMixin, Permission):
    message = _('MODULE_PERMISSION_MSG_NOT_VISIBLE')

    def has_permission(self, request, view):
        if not view.is_course_staff:
            module = view.module
            return self.has_object_permission(request, view, module)
        return True

    # pylint: disable-next=arguments-renamed
    def has_object_permission(self, request: HttpRequest, view: Any, module: CourseModule) -> bool:
        if isinstance(request.user, GraderUser):
            return False

        if not isinstance(module, CourseModule):
            return True

        if module.status == CourseModule.STATUS.HIDDEN:
            return False

        # Enrollment questionnaires are not affected by the module opening time.
        if hasattr(view, 'exercise') and view.exercise.status in (
                LearningObject.STATUS.ENROLLMENT,
                LearningObject.STATUS.ENROLLMENT_EXTERNAL,
                ):
            return True

        if not module.is_after_open():
            # FIXME: use format from django settings
            self.error_msg(
                _('MODULE_PERMISSION_ERROR_NOT_OPEN_YET -- {date}'),
                format={'date': module.opening_time},
                delim=' ',
            )
            return False

        if module.requirements.exists():
            points = CachedPoints(module.course_instance, request.user, view.is_course_staff)
            return module.are_requirements_passed(points)
        return True


CourseModulePermission = CourseModulePermissionBase | JWTInstanceReadPermission


class OnlyCourseTeacherPermission(Permission):
    message = _('COURSE_PERMISSION_MSG_ONLY_TEACHER')

    def has_permission(self, request, view):
        return self.has_object_permission(request, view, view.instance)

    def has_object_permission(self, request, view, obj):
        return view.is_teacher or request.user.is_superuser


class OnlyCourseStaffPermission(Permission):
    message = _('COURSE_PERMISSION_MSG_ONLY_COURSE_STAFF')

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


class OnlyEnrolledStudentOrCourseStaffPermission(Permission):
    message = _('COURSE_PERMISSION_MSG_ONLY_ENROLLED_STUDENTS_OR_COURSE_STAFF')

    def has_permission(self, request, view):
        return self.has_object_permission(request, view, None)

    def has_object_permission(self, request, view, obj):
        try:
            return view.is_student or view.is_course_staff or request.user.is_superuser
        except AttributeError:
            return False
