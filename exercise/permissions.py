from django.http import Http404
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

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
    SubmittedFile,
)


class ExerciseVisiblePermission(ObjectVisibleBasePermission):
    message = _('EXERCISE_VISIBILITY_PERMISSION_DENIED_MSG')
    model = LearningObject
    obj_var = 'exercise'

    def is_object_visible(self, request, view, exercise):
        """
        Find out if Exercise (LearningObject) is visible to user
        """
        if view.is_course_staff:
            return True

        if exercise.status == LearningObject.STATUS.HIDDEN:
            self.error_msg(_('EXERCISE_VISIBILITY_ERROR_NOT_VISIBLE'))
            return False

        if exercise.is_submittable and not exercise.course_module.have_exercises_been_opened():
            self.error_msg(
                format_lazy(
                    _('EXERCISE_VISIBILITY_ERROR_NOT_OPEN_YET -- {}'),
                    exercise.course_module.opening_time
                )
            )
            return False

        user = request.user
        if exercise.audience == LearningObject.AUDIENCE.REGISTERED_USERS:
            if not exercise.course_instance.is_student(user):
                self.error_msg(_('EXERCISE_VISIBLITY_ERROR_ONLY_RESISTERED_USERS'))
                return False
        elif exercise.audience == LearningObject.AUDIENCE.INTERNAL_USERS:
            if (not exercise.course_instance.is_student(user)
                    or user.userprofile.is_external):
                self.error_msg(_('EXERCISE_VISIBLITY_ERROR_ONLY_INTERNAL_USERS'))
                return False
        elif exercise.audience == LearningObject.AUDIENCE.EXTERNAL_USERS:
            if (not exercise.course_instance.is_student(user)
                    or not user.userprofile.is_external):
                self.error_msg(_('EXERCISE_VISIBLITY_ERROR_ONLY_EXTERNAL_USERS'))
                return False

        return True


class BaseExerciseAssistantPermission(ObjectVisibleBasePermission):
    message = _('EXERCISE_ASSISTANT_PERMISSION_DENIED_MSG')
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
                self.error_msg(_('EXERCISE_ASSISTANT_PERMISSION_ERROR_NO_ASSISTANT_VIEWING'))
                return False

        if access_mode == ACCESS.GRADING:
            if not (is_teacher or exercise.allow_assistant_grading):
                self.error_msg(_('EXERCISE_ASSISTANT_PERMISSION_NO_ASSISTANT_GRADING'))
                return False

        return True


class SubmissionVisiblePermission(ObjectVisibleBasePermission):
    message = _('SUBMISSION_VISIBILITY_PERMISSION_DENIED_MSG')
    model = Submission
    obj_var = 'submission'

    def is_object_visible(self, request, view, submission):
        if not (view.is_teacher or
                (view.is_assistant and submission.exercise.allow_assistant_viewing) or
                submission.is_submitter(request.user)):
            self.error_msg(_('SUBMISSION_VISIBILITY_ERROR_ONLY_SUBMITTER'))
            return False
        return True


class SubmissionVisibleFilter(FilterBackend):
    def filter_queryset(self, request, queryset, view):
        user = request.user
        is_super = user.is_staff or user.is_superuser
        if (
            issubclass(queryset.model, Submission) and
            not view.is_teacher and not is_super
        ):
            if view.is_assistant:
                queryset = queryset.filter(exercise__allow_assistant_viewing=True)
            else:
                queryset = queryset.filter(submitters=user.userprofile)
        return queryset


class SubmittedFileVisiblePermission(SubmissionVisiblePermission):
    model = SubmittedFile

    def is_object_visible(self, request, view, file):
        return super().is_object_visible(request, view, file.submission)


class ModelVisiblePermission(ObjectVisibleBasePermission):
    message = _('EXERCISE_MODEL_ANSWER_VISIBILITY_PERMISSION_DENIED_MSG')
    model = BaseExercise
    obj_var = 'exercise'

    def is_object_visible(self, request, view, exercise):
        """
        Find out if exercise's model answer is visible to user
        """
        if view.is_course_staff:
            return True

        if not exercise.can_show_model_solutions_to_student(request.user):
            self.error_msg(_('EXERCISE_MODEL_ANSWER_VISIBILITY_ERROR_NOT_ALLOWED_VIEWING'))
            return False

        return True
