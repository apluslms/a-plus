import json
import logging
import time
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db.models import F
from django.http.response import JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from course.viewbase import CourseInstanceBaseView, CourseInstanceMixin
from course.models import (
    USERTAG_EXTERNAL,
    USERTAG_INTERNAL,
)
from deviations.models import MaxSubmissionsRuleDeviation
from lib.helpers import settings_text, extract_form_errors
from lib.viewbase import BaseRedirectView, BaseFormView, BaseView
from notification.models import Notification
from authorization.permissions import ACCESS
from .models import LearningObject
from .forms import (
    SubmissionReviewForm,
    SubmissionCreateAndReviewForm,
    EditSubmittersForm,
)
from .submission_models import Submission
from .viewbase import (
    ExerciseBaseView,
    SubmissionBaseView,
    SubmissionMixin,
    ExerciseMixin,
)


logger = logging.getLogger('aplus.exercise')


class ListSubmissionsView(ExerciseBaseView):
    access_mode = ACCESS.ASSISTANT
    template_name = "exercise/staff/list_submissions.html"
    ajax_template_name = "exercise/staff/_submissions_table.html"
    default_limit = 50

    def get_common_objects(self):
        super().get_common_objects()
        if not self.exercise.is_submittable:
            raise Http404()
        qs = self.exercise.submissions\
            .defer("feedback", "submission_data", "grading_data")\
            .prefetch_related('submitters').all()
        self.all = self.request.GET.get('all', None)
        self.all_url = self.exercise.get_submission_list_url() + "?all=yes"
        self.submissions = qs if self.all else qs[:self.default_limit]
        self.note("all", "all_url", "submissions", "default_limit")


class SubmissionsSummaryView(ExerciseBaseView):
    access_mode = ACCESS.ASSISTANT
    template_name = "exercise/staff/submissions_summary.html"


class InspectSubmissionView(SubmissionBaseView):
    access_mode = ACCESS.ASSISTANT
    template_name = "exercise/staff/inspect_submission.html"

    def get_common_objects(self):
        super().get_common_objects()
        self.get_summary_submissions()


class ResubmitSubmissionView(SubmissionMixin, BaseRedirectView):
    access_mode = ACCESS.ASSISTANT

    def post(self, request, *args, **kwargs):
        page = self.exercise.grade(request, self.submission)
        for error in page.errors:
            messages.error(request, error)
        return self.redirect(self.submission.get_inspect_url())


class IncreaseSubmissionMaxView(SubmissionMixin, BaseRedirectView):
    access_mode = ACCESS.GRADING

    def post(self, request, *args, **kwargs):
        deviation,_ = MaxSubmissionsRuleDeviation.objects.get_or_create(
            exercise=self.exercise,
            submitter=self.submission.submitters.first(),
            defaults={'extra_submissions': 0}
        )
        MaxSubmissionsRuleDeviation.objects\
            .filter(id=deviation.id)\
            .update(extra_submissions=(F('extra_submissions') + 1))
        return self.redirect(self.submission.get_inspect_url())



class AssessSubmissionView(SubmissionMixin, BaseFormView):
    """
    Allows manual assessing of a submission. Changing the grade or writing
    feedback will send a notification to the submitters. Late submission
    penalty is not applied to the grade.
    """
    access_mode = ACCESS.GRADING
    template_name = "exercise/staff/assess_submission.html"
    form_class = SubmissionReviewForm

    def get_initial(self):
        return {
            "points": self.submission.grade,
            "feedback": self.submission.feedback,
            "assistant_feedback": self.submission.assistant_feedback,
        }

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["exercise"] = self.exercise
        return kwargs

    def get_success_url(self):
        return self.submission.get_inspect_url()

    def form_valid(self, form):
        assistant_feedback = form.cleaned_data["assistant_feedback"]
        feedback = form.cleaned_data["feedback"]

        note = ""
        if self.submission.assistant_feedback != assistant_feedback:
            note = assistant_feedback
        elif self.submission.feedback != feedback:
            note = feedback

        self.submission.set_points(form.cleaned_data["points"],
            self.exercise.max_points, no_penalties=True)
        self.submission.grader = self.profile
        self.submission.assistant_feedback = assistant_feedback
        self.submission.feedback = feedback
        self.submission.set_ready()
        self.submission.save()

        #sub = _('Feedback to {name}').format(name=self.exercise)
        #msg = _('<p>You have new personal feedback to exercise '
        #        '<a href="{url}">{name}</a>.</p>{message}').format(
        #    url=self.submission.get_absolute_url(),
        #    name=self.exercise,
        #    message=note,
        #)
        Notification.send(self.profile, self.submission)

        messages.success(self.request, _('ASSESS_SUBMISSION_REVIEW_SAVED_SUCCESS'))
        return super().form_valid(form)


class FetchMetadataView(CourseInstanceMixin, BaseView):
    access_mode = ACCESS.TEACHER

    def get(self, request, *args, **kwargs):
        exercise_url = request.GET.get("exercise_url", None)
        metadata = {"success": False}
        validate = URLValidator()
        try:
            validate(exercise_url)
            lobject = LearningObject(service_url=exercise_url)
            page = lobject.load(request, [])
            if page.is_loaded:
                metadata["name"] = page.meta["title"]
                metadata["description"] = page.meta["description"]
                metadata["success"] = True
            else:
                metadata["message"] = str(_('ERROR_FAILED_TO_LOAD_RESOURCE'))
        except ValidationError as e:
            metadata["message"] = " ".join(e.messages)
        return JsonResponse(metadata)


class AllResultsView(CourseInstanceBaseView):
    access_mode = ACCESS.TEACHER
    template_name = "exercise/staff/results.html"

    def get_common_objects(self):
        super().get_common_objects()
        self.tags = [USERTAG_INTERNAL, USERTAG_EXTERNAL]
        self.tags.extend(self.instance.usertags.all())
        self.note(
            'tags',
        )


class AnalyticsView(CourseInstanceBaseView):
    access_mode = ACCESS.TEACHER
    template_name = "exercise/staff/analytics.html"

    def get_common_objects(self):
        super().get_common_objects()
        self.tags = list(self.instance.usertags.all())
        self.internal_user_label = settings_text('INTERNAL_USER_LABEL')
        self.external_user_label = settings_text('EXTERNAL_USER_LABEL')
        self.note(
            'tags', 'internal_user_label', 'external_user_label',
        )


class UserResultsView(CourseInstanceBaseView):
    access_mode = ACCESS.ASSISTANT
    template_name = "exercise/staff/user_results.html"
    user_kw = 'user_id'

    def get_resource_objects(self):
        super().get_resource_objects()
        self.student = get_object_or_404(
            User,
            id=self.kwargs[self.user_kw],
        )
        self.note('student')

    def get_common_objects(self):
        profile = self.student.userprofile
        exercise = LearningObject.objects.find_enrollment_exercise(
            self.instance,
            profile
        )
        if exercise:
            exercise = exercise.as_leaf_class()
            submissions = exercise.get_submissions_for_student(profile)
        else:
            submissions = []
        self.enrollment_exercise = exercise
        self.enrollment_submissions = submissions
        self.note('enrollment_exercise', 'enrollment_submissions')


class CreateSubmissionView(ExerciseMixin, BaseRedirectView):
    """
    Creates a new assessed submission for a selected student without
    notifying the student.
    """
    access_mode = ACCESS.TEACHER

    def post(self, request, *args, **kwargs):

        # Use form to parse and validate the request.
        form = SubmissionCreateAndReviewForm(
            request.POST,
            exercise=self.exercise,
            students_choices=self.instance.get_student_profiles()
        )
        if not form.is_valid():
            messages.error(request,
                _("ERROR_INVALID_POST_DATA -- {error}").format(
                    error="\n".join(extract_form_errors(form))))
            return self.redirect(self.exercise.get_submission_list_url())

        sub = Submission.objects.create(exercise=self.exercise)
        sub.submitters.set(form.cleaned_students)
        sub.feedback = form.cleaned_data.get("feedback")
        sub.set_points(form.cleaned_data.get("points"),
            self.exercise.max_points, no_penalties=True)
        sub.submission_time = form.cleaned_data.get("submission_time")
        sub.grader = self.profile
        sub.grading_time = timezone.now()
        sub.set_ready()
        sub.save()

        messages.success(request, _('NEW_SUBMISSION_STORED'))
        return self.redirect(sub.get_absolute_url())


class EditSubmittersView(SubmissionMixin, BaseFormView):
    access_mode = ACCESS.TEACHER
    template_name = "exercise/staff/edit_submitters.html"
    form_class = EditSubmittersForm

    def get_common_objects(self):
        self.groups = self.instance.groups.all()
        self.note('groups')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.submission
        return kwargs

    def get_success_url(self):
        return self.submission.get_inspect_url()

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _('SUCCESS_SAVING_CHANGES'))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _('FAILURE_SAVING_CHANGES'))
        return super().form_invalid(form)
