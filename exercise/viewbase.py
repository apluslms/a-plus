from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from course.viewbase import CourseModuleMixin
from lib.viewbase import BaseTemplateView
from userprofile.viewbase import ACCESS
from .models import LearningObject, Submission


class ExerciseMixin(CourseModuleMixin):
    exercise_kw = "exercise_path"

    def get_resource_objects(self):
        super().get_resource_objects()
        path = self._get_kwarg(self.exercise_kw).split('/')
        self.exercise = get_object_or_404(
            LearningObject,
            course_module=self.module,
            url=path[-1],
        ).as_leaf_class()
        self.note("exercise")

        def recursive_check(lobject, i):
            if lobject.url != path[i]:
                raise Http404()
            if lobject.parent:
                recursive_check(lobject.parent, i - 1)
        recursive_check(self.exercise, len(path) - 1)

    def access_control(self):
        super().access_control()
        if not self.is_course_staff \
                and self.exercise.status == LearningObject.STATUS_HIDDEN:
            raise Http404()
        if self.access_mode == ACCESS.GRADING:
            if not (self.is_teacher or self.exercise.allow_assistant_grading):
                messages.error(self.request,
                    _("Assistant grading is not allowed for this exercise."))
                raise PermissionDenied()


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
                messages.error(self.request,
                    _("Only the submitter shall pass."))
                raise PermissionDenied()


class SubmissionBaseView(SubmissionMixin, BaseTemplateView):
    pass
