from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from course.viewbase import CourseModuleMixin
from lib.viewbase import BaseTemplateView
from authorization.permissions import ACCESS
from .permissions import (
    ExerciseVisiblePermission,
    BaseExerciseAssistantPermission,
    SubmissionVisiblePermission,
)
from .models import (
    LearningObject,
    BaseExercise,
    Submission,
)


class ExerciseBaseMixin(object):
    exercise_kw = "exercise_path"
    exercise_permission_classes = (
        ExerciseVisiblePermission,
    )

    def get_permissions(self):
        perms = super().get_permissions()
        perms.extend((Perm() for Perm in self.exercise_permission_classes))
        return perms

    # get_exercise_object

    def get_resource_objects(self):
        super().get_resource_objects()
        self.exercise = self.get_exercise_object()
        self.note("exercise")


class ExerciseMixin(ExerciseBaseMixin, CourseModuleMixin):
    exercise_permission_classes = ExerciseBaseMixin.exercise_permission_classes + (
        BaseExerciseAssistantPermission,
    )

    def get_exercise_object(self):
        path = self.kwargs[self.exercise_kw].split('/')
        exercise = self.module._children().by_path(path)
        if not exercise:
            raise Http404("Learning object not found")
        return exercise.as_leaf_class()


class ExerciseBaseView(ExerciseMixin, BaseTemplateView):
    pass


class SubmissionBaseMixin(object):
    submission_kw = "submission_id"
    submission_permission_classes = (
        SubmissionVisiblePermission,
    )

    def get_permissions(self):
        perms = super().get_permissions()
        perms.extend((Perm() for Perm in self.submission_permission_classes))
        return perms

    # get_submission_object

    def get_resource_objects(self):
        super().get_resource_objects()
        self.submission = self.get_submission_object()
        self.note("submission")


class SubmissionMixin(SubmissionBaseMixin, ExerciseMixin):
    def get_submission_object(self):
        return get_object_or_404(
            Submission,
            id=self.kwargs[self.submission_kw],
            exercise=self.exercise
        )


class SubmissionBaseView(SubmissionMixin, BaseTemplateView):
    pass
