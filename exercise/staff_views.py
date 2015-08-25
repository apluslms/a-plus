import json
import logging
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.http.response import JsonResponse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.views.generic.base import View

from course.viewbase import CourseInstanceBaseView, CourseInstanceMixin
from lib.viewbase import BaseRedirectView, BaseFormView
from notification.models import Notification
from userprofile.viewbase import ACCESS
from .models import BaseExercise
from .presentation.results import ResultTable
from .forms import SubmissionReviewForm, SubmissionCreateAndReviewForm
from .submission_models import Submission
from .viewbase import ExerciseBaseView, SubmissionBaseView, SubmissionMixin, \
    ExerciseMixin


logger = logging.getLogger('aplus.exercise')


class ListSubmissionsView(ExerciseBaseView):
    access_mode = ACCESS.ASSISTANT
    template_name = "exercise/staff/list_submissions.html"
    ajax_template_name = "exercise/staff/_submissions_table.html"

    def get_common_objects(self):
        super().get_common_objects()
        self.submissions = self.exercise.submissions.all()
        self.note("submissions")


class InspectSubmissionView(SubmissionBaseView):
    access_mode = ACCESS.ASSISTANT
    template_name = "exercise/staff/inspect_submission.html"


class ResubmitSubmissionView(SubmissionMixin, BaseRedirectView):
    access_mode = ACCESS.ASSISTANT

    def post(self, request, *args, **kwargs):
        self.handle()
        _ = self.exercise.grade(request, self.submission)
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

        sub = _('Feedback to {name}').format(name=self.exercise)
        msg = _('<p>You have new personal feedback to exercise '
                '<a href="{url}">{name}</a>.</p>{message}').format(
            url=self.submission.get_absolute_url(),
            name=self.exercise,
            message=note,
        )
        for student in self.submission.submitters.all():
            Notification.send(self.profile, student, self.instance, sub, msg)

        messages.success(self.request, _("The review was saved successfully "
            "and the submitters were notified."))
        return super().form_valid(form)


class FetchMetadataView(CourseInstanceMixin, View):
    access_mode = ACCESS.TEACHER

    def get(self, request, *args, **kwargs):
        self.handle()
        exercise_url = request.GET.get("exercise_url", None)
        metadata = {"success": False}
        validate = URLValidator()
        try:
            validate(exercise_url)
            exercise = BaseExercise(service_url=exercise_url)
            page = exercise.load(request, [])
            if page.is_loaded:
                metadata["name"] = page.meta["title"]
                metadata["description"] = page.meta["description"]
                metadata["success"] = True
            else:
                metadata["message"] = _("Failed to load the resource.")
        except ValidationError as e:
            metadata["message"] = " ".join(e.messages)
        return JsonResponse(metadata)


class AllResultsView(CourseInstanceBaseView):
    access_mode = ACCESS.TEACHER
    template_name = "exercise/staff/results.html"

    def get_common_objects(self):
        super().get_common_objects()
        self.table = ResultTable(self.instance)
        self.note("table")


class CreateSubmissionView(ExerciseMixin, BaseRedirectView):
    """
    Creates a new assessed submission for a selected student without
    notifying the student.
    """
    access_mode = ACCESS.TEACHER

    def post(self, request, *args, **kwargs):
        self.handle()

        # Use form to parse and validate the request.
        form = SubmissionCreateAndReviewForm(
            request.POST,
            exercise=self.exercise,
            students_choices=self.instance.get_student_profiles()
        )
        if not form.is_valid():
            messages.error(request,
                _("Invalid POST data:\n{error}").format(
                    error="\n".join(extract_form_errors(form))))
            return self.redirect(self.exercise.get_submission_list_url())

        sub = Submission.objects.create(exercise=self.exercise)
        sub.submitters = form.cleaned_data.get("students") \
            or form.cleaned_data.get("students_by_student_id")
        sub.feedback = form.cleaned_data.get("feedback")
        sub.set_points(form.cleaned_data.get("points"),
            self.exercise.max_points, no_penalties=True)
        sub.submission_time = form.cleaned_data.get("submission_time")
        sub.grader = self.profile
        sub.grading_time = timezone.now()
        sub.set_ready()
        sub.save()

        messages.success(request, _("New submission stored."))
        return self.redirect(sub.get_absolute_url())
