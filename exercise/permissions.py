from django.http import Http404
from django.utils.translation import ugettext_lazy as _

from authorization.permissions import (
    ACCESS,
    Permission,
    ObjectVisibleBasePermission,
    FilterBackend,
)
from .models import (
    LearningObject,
    BaseExercise,
    Submission,
)


class ExerciseVisiblePermission(ObjectVisibleBasePermission):
    message = _("Permission denied by exercise visibility")
    model = LearningObject
    obj_var = 'exercise'

    def is_object_visible(self, request, view, exercise):
        """
        Find out if Exercise (LearningObject) is visible to user
        """
        if view.is_course_staff:
            return True

        if exercise.status == LearningObject.STATUS.HIDDEN:
            self.error_msg(request, _("The exercise is not currently visible."))
            return False

        user = request.user
        if exercise.audience == LearningObject.AUDIENCE.REGISTERED_USERS:
            if not exercise.course_instance.is_student(user):
                self.error_msg(request, _("The exercise is only for registered users."))
                return False
        elif exercise.audience == LearningObject.AUDIENCE.INTERNAL_USERS:
            if (not exercise.course_instance.is_student(user)
                    or user.userprofile.is_external):
                self.error_msg(request, _("The exercise is only for internal users."))
                return False
        elif exercise.audience == LearningObject.AUDIENCE.EXTERNAL_USERS:
            if (not exercise.course_instance.is_student(user)
                    or not user.userprofile.is_external):
                self.error_msg(request, _("The exercise is only for external users."))
                return False

        return True


class BaseExerciseAssistantPermission(ObjectVisibleBasePermission):
    message = _("Permission denied by exercise assistant permission")
    model = BaseExercise
    obj_var = 'exercise'

    def is_object_visible(self, request, view, exercise):
        """
        Make sure views that require assistant are also visible to them.
        Also if view is for grading, make sure assistant is allowed to grade.

        We expect that AccessModePermission is checked first
        """
        access_mode = view.get_access_mode()
        is_teacher = view.is_teacher

        # NOTE: AccessModePermission will make sure that user
        # is assistant when access_mode >= ACCESS.ASSISTANT

        if access_mode >= ACCESS.ASSISTANT:
            if not (is_teacher or exercise.allow_assistant_viewing):
                self.error_msg(request,
                    _("Assistant viewing is not allowed for this exercise."))
                return False

        if access_mode == ACCESS.GRADING:
            if not (is_teacher or exercise.allow_assistant_grading):
                self.error_msg(request,
                    _("Assistant grading is not allowed for this exercise."))
                return False

        return True


class SubmissionVisiblePermission(ObjectVisibleBasePermission):
    message = _("Permission denied by submission visibility")
    model = Submission
    obj_var = 'submission'

    def is_object_visible(self, request, view, submission):
        if not (view.is_course_staff or submission.is_submitter(request.user)):
            self.error_msg(request, _("Only the submitter shall pass."))
            return False
        return True


class SubmissionVisibleFilter(FilterBackend):
    def filter_queryset(self, request, queryset, view):
        user = request.user
        is_super = user.is_staff or user.is_superuser
        is_staff = view.is_course_staff
        if issubclass(queryset.model, Submission) and not is_super and not is_staff:
            queryset = queryset.filter(submitters=user.userprofile)
        return queryset
