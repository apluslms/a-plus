from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import get_object_or_404

from course.viewbase import CourseModuleAccessMixin, CourseInstanceMixin
from lib.viewbase import BaseTemplateView
from userprofile.viewbase import ACCESS
from .models import LearningObject, Submission


class ExerciseMixin(CourseModuleAccessMixin, CourseInstanceMixin):
    exercise_kw = "exercise_id"

    def get_resource_objects(self):
        super().get_resource_objects()
        self.exercise = get_object_or_404(
            LearningObject,
            id=self._get_kwarg(self.exercise_kw),
            course_module__course_instance=self.instance
        ).as_leaf_class()
        self.module = self.exercise.course_module
        self.note("exercise", "module")

    def access_control(self):
        super().access_control()
        if self.access_mode == ACCESS.GRADING:
            if not (self.is_teacher or self.exercise.allow_assistant_grading):
                raise PermissionDenied(
                    _("Assistant grading is not allowed for this exercise."))


class ExerciseBaseView(ExerciseMixin, BaseTemplateView):
    pass


class SubmissionMixin(ExerciseMixin):
    submission_kw = "submission_id"

    def get_resource_objects(self):
        super().get_resource_objects()
        self.submission = get_object_or_404(
            Submission,
            id=self._get_kwarg(self.submission_kw),
            exercise=self.exercise
        )
        self.note("submission")

    def access_control(self):
        super().access_control()
        if not (self.is_course_staff \
            or self.submission.is_submitter(self.request.user)):
                raise PermissionDenied()


class SubmissionBaseView(SubmissionMixin, BaseTemplateView):
    pass
