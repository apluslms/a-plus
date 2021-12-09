from typing import Optional

from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from authorization.permissions import ACCESS
from course.viewbase import CourseModuleMixin
from lib.viewbase import BaseTemplateView, BaseView
from .cache.hierarchy import NoSuchContent
from .cache.points import CachedPoints
from .exercise_summary import UserExerciseSummary
from .permissions import (
    ExerciseVisiblePermission,
    BaseExerciseAssistantPermission,
    SubmissionVisiblePermission,
    ModelVisiblePermission,
)
from .models import (
    LearningObject,
    BaseExercise,
    Submission,
    RevealRule,
)
from .reveal_states import ExerciseRevealState


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


class ExerciseRevealRuleMixin:
    def get_resource_objects(self) -> None:
        super().get_resource_objects()
        self.get_feedback_visibility()
        self.get_model_visibility()

    def get_feedback_visibility(self) -> None:
        self.feedback_revealed = True
        self.feedback_hidden_description = None
        if (
            not self.is_course_staff
            and isinstance(self.exercise, BaseExercise)
            and isinstance(self.request.user, User)
        ):
            rule = self.exercise.active_submission_feedback_reveal_rule
            state = ExerciseRevealState(self.exercise, self.request.user)
            self.feedback_revealed = rule.is_revealed(state)
            if rule.trigger in (
                RevealRule.TRIGGER.TIME,
                RevealRule.TRIGGER.DEADLINE,
                RevealRule.TRIGGER.DEADLINE_ALL,
            ):
                reveal_time = rule.get_reveal_time(state)
                formatted_time = date_format(timezone.localtime(reveal_time), "DATETIME_FORMAT")
                self.feedback_hidden_description = format_lazy(
                    _('RESULTS_WILL_BE_REVEALED -- {time}'),
                    time=formatted_time,
                )
            else:
                self.feedback_hidden_description = _('RESULTS_ARE_CURRENTLY_HIDDEN')
        self.note("feedback_revealed", "feedback_hidden_description")

    def get_model_visibility(self) -> None:
        self.model_revealed = True
        if (
            not self.is_course_staff
            and isinstance(self.exercise, BaseExercise)
            and isinstance(self.request.user, User)
        ):
            self.model_revealed = self.exercise.can_show_model_solutions_to_student(self.request.user)
        self.note("model_revealed")


class ExerciseMixin(ExerciseRevealRuleMixin, ExerciseBaseMixin, CourseModuleMixin):
    exercise_permission_classes = ExerciseBaseMixin.exercise_permission_classes + (
        BaseExerciseAssistantPermission,
    )

    def get_exercise_object(self):
        try:
            exercise_id = self.content.find_path(
                self.module.id,
                self.kwargs[self.exercise_kw]
            )
            return LearningObject.objects.get(id=exercise_id).as_leaf_class()
        except (NoSuchContent, LearningObject.DoesNotExist):
            raise Http404("Learning object not found")

    def get_common_objects(self) -> None:
        super().get_common_objects()
        self.get_cached_points()
        self.now = timezone.now()
        cur, tree, prev, nex = self.content.find(self.exercise)
        self.previous = prev
        self.current = cur
        self.next = nex
        self.breadcrumb = tree[1:-1]
        self.note("now", "previous", "current", "next", "breadcrumb")

    def get_summary_submissions(self, user: Optional[User] = None) -> None:
        self.summary = UserExerciseSummary(
            self.exercise, user or self.request.user
        )
        self.submissions = self.summary.get_submissions()
        self.note("summary", "submissions")

    def get_cached_points(self, user: Optional[User] = None) -> None:
        cache = CachedPoints(self.instance, user or self.request.user, self.content, self.is_course_staff)
        entry, _, _, _ = cache.find(self.exercise)
        self.cached_points = entry
        self.note("cached_points")


class ExerciseBaseView(ExerciseMixin, BaseTemplateView):
    pass


class ExerciseTemplateBaseView(ExerciseMixin, BaseTemplateView):
    pass


class ExerciseModelMixin(ExerciseMixin):
    model_permission_classes = (
        ModelVisiblePermission,
    )

    def get_permissions(self):
        perms = super().get_permissions()
        perms.extend((Perm() for Perm in self.model_permission_classes))
        return perms

    def get_exercise_object(self):
        exercise = super().get_exercise_object()
        if not exercise.is_submittable:
            raise Http404("This learning object does not have a model answer.")
        return exercise

class ExerciseModelBaseView(ExerciseModelMixin, BaseTemplateView):
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

    def get_resource_objects(self) -> None:
        super().get_resource_objects()
        self.submission = self.get_submission_object()
        if self.submission.is_submitter(self.request.user):
            self.submitter = self.request.user.userprofile
        else:
            self.submitter = self.submission.submitters.first()
        self.note("submission", "submitter")


class SubmissionMixin(SubmissionBaseMixin, ExerciseMixin):

    def get_submission_object(self):
        return get_object_or_404(
            Submission,
            id=self.kwargs[self.submission_kw],
            exercise=self.exercise
        )

    def get_summary_submissions(self, user: Optional[User] = None) -> None:
        super().get_summary_submissions(user or self.submitter.user)
        self.index = len(self.submissions) - list(self.submissions).index(self.submission)
        self.note("index")

    def get_cached_points(self, user: Optional[User] = None) -> None:
        super().get_cached_points(user or self.submitter.user)


class SubmissionBaseView(SubmissionMixin, BaseTemplateView):
    pass

class SubmissionDraftBaseView(ExerciseMixin, BaseView):
    pass
