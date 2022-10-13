import logging
from typing import Any, Dict

from django.contrib import messages
from django.contrib.auth.models import User # pylint: disable=imported-auth-user
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.validators import URLValidator
from django.db.models import Count, Max, Prefetch, Q
from django.http.request import HttpRequest
from django.http.response import HttpResponse, JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls.base import reverse
from django.utils import timezone
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _, ngettext

from authorization.permissions import ACCESS
from course.viewbase import CourseInstanceBaseView, CourseInstanceMixin
from course.models import (
    Enrollment,
    USERTAG_EXTERNAL,
    USERTAG_INTERNAL,
)
from deviations.models import MaxSubmissionsRuleDeviation
from exercise.cache.points import CachedPoints
from lib.helpers import settings_text, extract_form_errors
from lib.viewbase import BaseRedirectView, BaseFormView, BaseView
from notification.models import Notification
from userprofile.models import UserProfile
from .models import BaseExercise, ExerciseTask, LearningObject, Submission
from .forms import (
    SubmissionReviewForm,
    SubmissionCreateAndReviewForm,
    EditSubmittersForm,
)
from .tasks import regrade_exercises
from .viewbase import (
    ExerciseBaseView,
    SubmissionBaseView,
    SubmissionMixin,
    ExerciseMixin,
    ExerciseListBaseView,
)
from lib.logging import SecurityLog


logger = logging.getLogger('aplus.exercise')


class ListSubmissionsView(ExerciseListBaseView):
    access_mode = ACCESS.ASSISTANT
    template_name = "exercise/staff/list_submissions.html"
    ajax_template_name = "exercise/staff/_submissions_table.html"
    default_limit = 50

    def get_common_objects(self) -> None:
        super().get_common_objects()
        if not self.exercise.is_submittable:
            raise Http404()
        qs = (
            self.exercise.submissions
            .defer("feedback", "submission_data", "grading_data")
            .prefetch_related(None)
            .prefetch_related(
                Prefetch('submitters', UserProfile.objects.prefetch_tags(self.instance)),
            )
        )
        self.all = self.request.GET.get('all', None)
        self.all_url = self.exercise.get_submission_list_url() + "?all=yes"
        self.submissions = qs if self.all else qs[:self.default_limit]
        self.note("all", "all_url", "submissions", "default_limit")


class SubmissionsSummaryView(ExerciseBaseView):
    access_mode = ACCESS.ASSISTANT
    template_name = "exercise/staff/submissions_summary.html"


class ListSubmittersView(ExerciseListBaseView):
    """
    Similar to ListSubmissionsView, but lists submitters instead of individual
    submissions.
    """
    access_mode = ACCESS.ASSISTANT
    template_name = "exercise/staff/list_submitters.html"
    ajax_template_name = "exercise/staff/_submitters_table.html"

    def get_common_objects(self) -> None:
        super().get_common_objects()
        if not self.exercise.is_submittable:
            raise Http404()
        self.submitters = []

        # The points, submission counts and submission times are retrieved
        # using a QuerySet instead of CachedPoints or UserExerciseSummary,
        # because those are specific to a single student, and this page is
        # supposed to list all students.
        submitter_summaries = (
            self.exercise.submissions
            .values('submitters__id')
            .annotate(
                count_submissions=Count('id'),
                count_assessed=Count('id', filter=Q(grader__isnull=False)),
                last_submission_time=Max('submission_time'),
            )
            .annotate_submitter_points('final_points')
            .order_by()
        )

        # Get a dict of submitters, accessed by their id.
        profiles = (
            UserProfile.objects
            .filter(submissions__exercise=self.exercise)
            .prefetch_tags(self.instance)
            .in_bulk()
        )
        # Add UserProfile instances to the dicts in submitter_summaries, so we can
        # use the 'profiles' template tag.
        for submitter_summary in submitter_summaries:
            submitter_id = submitter_summary.get('submitters__id')
            # Avoid crashing if there are submissions with no submitters.
            if submitter_id is not None:
                profile = profiles[submitter_id]
                self.submitters.append({'profile': profile, **submitter_summary})
        self.note('submitters')


class InspectSubmitterView(ExerciseBaseView, BaseRedirectView):
    """
    Redirects to the inspect page of the user' best submission.
    """
    access_mode = ACCESS.ASSISTANT
    user_kw = 'user_id'

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        user = get_object_or_404(
            User,
            id=self.kwargs[self.user_kw],
        )

        # Find the submitter's best submission using the cache.
        cache = CachedPoints(self.instance, user, self.content, True)
        ids = cache.submission_ids(exercise_id=self.exercise.id, best=True, fallback_to_last=True)
        if not ids:
            raise Http404()
        del kwargs['user_id']
        url = reverse(
            'submission-inspect',
            kwargs={'submission_id': ids[0], **kwargs},
        )
        return self.redirect(url)


class InspectSubmissionView(SubmissionBaseView, BaseFormView):
    access_mode = ACCESS.ASSISTANT
    template_name = "exercise/staff/inspect_submission.html"
    form_class = SubmissionReviewForm

    def get_common_objects(self) -> None:
        super().get_common_objects()
        self.get_summary_submissions()
        self.files = list(self.submission.files.all())

        self.lowest_visible_index = self.index - 10
        self.highest_visible_index = self.index + 10

        # Find out if there are other submissions that the user should be
        # notified about (better submissions, later submissions or the final
        # submission).
        self.not_final = False
        self.not_best = False
        self.not_last = False
        for submission in self.submissions:
            if submission.id != self.submission.id:
                if submission.force_exercise_points:
                    self.not_final = True
                    # When not_final is True, the other variables are not needed. Stop the loop early.
                    break
                if ((submission.grade > self.submission.grade and submission.status != Submission.STATUS.UNOFFICIAL)
                        or (self.submission.status == Submission.STATUS.UNOFFICIAL
                            and submission.status != Submission.STATUS.UNOFFICIAL)):
                    self.not_best = True
                if (submission.submission_time > self.submission.submission_time
                        and submission.status != Submission.STATUS.UNOFFICIAL):
                    self.not_last = True

        if self.exercise.grading_mode == BaseExercise.GRADING_MODE.BEST:
            mode = _('GRADING_MODE_BEST')
        elif self.exercise.grading_mode == BaseExercise.GRADING_MODE.LAST:
            mode = _('GRADING_MODE_LAST')
        else:
            logger.warning("Missing description for grading mode.")
        self.grading_mode_text = format_lazy(_('GRADING_MODE_TITLE -- {}'), mode)

        self.note(
            'files',
            'lowest_visible_index',
            'highest_visible_index',
            'not_final',
            'not_best',
            'not_last',
            'grading_mode_text',
        )

    def get_initial(self):
        return {
            "points": self.submission.grade,
            "assistant_feedback": self.submission.assistant_feedback,
            "feedback": self.submission.feedback,
            "mark_as_final": self.submission.force_exercise_points,
        }

    def get_form_kwargs(self) -> Dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["exercise"] = self.exercise
        kwargs["help_texts_to_tooltips"] = True
        return kwargs

    def get_success_url(self) -> str:
        return self.submission.get_inspect_url()

    def form_valid(self, form: SubmissionReviewForm) -> HttpResponse:
        if not (self.is_teacher or self.exercise.allow_assistant_grading):
            messages.error(self.request, _('EXERCISE_ASSISTANT_PERMISSION_NO_ASSISTANT_GRADING'))
            raise PermissionDenied()

        assistant_feedback = form.cleaned_data["assistant_feedback"]
        feedback = form.cleaned_data["feedback"]

        self.submission.set_points(form.cleaned_data["points"],
            self.exercise.max_points, no_penalties=True)
        SecurityLog.logevent(self.request, "set-points",
            "exercise: {}, submission ID: {}, submitter: {}, points: {}".format(
                self.get_submission_object().exercise,
                self.submission.id,
                self.submission.submitters.first().user.username,
                form.cleaned_data["points"]
            )
        )
        self.submission.force_exercise_points = form.cleaned_data["mark_as_final"]
        self.submission.grader = self.profile
        self.submission.assistant_feedback = assistant_feedback
        self.submission.feedback = feedback
        self.submission.set_ready()
        self.submission.save()

        # Set other submissions as not final if this one is final.
        if self.submission.force_exercise_points:
            other_submissions = (self.exercise
                .get_submissions_for_student(self.submission.submitters.first())
                .filter(force_exercise_points=True)
                .exclude(id=self.submission.id))
            for submission in other_submissions:
                submission.force_exercise_points = False
                submission.save()

        Notification.send(self.profile, self.submission)

        messages.success(self.request, _('ASSESS_SUBMISSION_REVIEW_SAVED_SUCCESS'))
        return super().form_valid(form)


class ResubmitSubmissionView(SubmissionMixin, BaseRedirectView):
    access_mode = ACCESS.ASSISTANT

    def post(self, request, *args, **kwargs):
        page = self.exercise.grade(self.submission, request)
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
        deviation.extra_submissions += 1
        deviation.granter = request.user.userprofile
        deviation.save()
        return self.redirect(self.submission.get_inspect_url())


class StartRegradeView(ExerciseBaseView, BaseRedirectView):
    access_mode = ACCESS.TEACHER

    def post(self, request, *args, **kwargs):
        regrade_type = request.POST.get('regrade_type')
        if regrade_type not in ['all', 'incomplete']:
            logger.debug("Invalid regrade_type")
            return self.redirect(self.exercise.get_url('submission-list'))

        # If there already was regrade ongoing, continue with that and don't start again
        if not ExerciseTask.objects.filter(
            exercise=self.exercise,
            task_type=ExerciseTask.TASK_TYPE.REGRADE
        ).exists():
            task, created = ExerciseTask.objects.get_or_create(
                exercise=self.exercise,
                task_type=ExerciseTask.TASK_TYPE.REGRADE,
            )
            if created:
                result = regrade_exercises.delay(self.exercise.id, regrade_type)
                task.task_id = result.id
                task.save()
                messages.info(request, _("NEW_REGRADE_TASK_CREATED"))
            else:
                messages.warning(request, _("REGRADE_ALREADY_RUNNING"))
        else:
            messages.warning(request, _("REGRADE_ALREADY_RUNNING"))

        return self.redirect(self.exercise.get_url('submission-list'))


class NextUnassessedSubmitterView(ExerciseBaseView, BaseRedirectView):
    """
    Redirect to the inspect page of the best submission of the first submitter
    whose submissions have not been assessed yet.
    """
    access_mode = ACCESS.ASSISTANT

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        # Query submitters who have not been assessed yet.
        submitter = None
        submitters = (UserProfile.objects
            .filter(submissions__exercise=self.exercise)
            .annotate(
                count_assessed=Count(
                    'submissions__id',
                    filter=(Q(submissions__grader__isnull=False)),
                ),
            )
            .filter(count_assessed=0)
            .order_by('id'))

        previous_user_id = request.GET.get('prev')
        if previous_user_id:
            # Find specifically the submitter AFTER the previously inspected one.
            submitters_after = submitters.filter(id__gt=previous_user_id)
            submitter = submitters_after.first()

        if not submitter:
            submitter = submitters.first()

        if not submitter:
            # There are no more unassessed submitters.
            messages.success(request, _('ALL_SUBMITTERS_HAVE_BEEN_ASSESSED'))
            return self.redirect(self.exercise.get_submission_list_url())

        # Find the submitter's best submission using the cache.
        cache = CachedPoints(self.instance, submitter.user, self.content, True)
        ids = cache.submission_ids(exercise_id=self.exercise.id, best=True, fallback_to_last=True)
        if not ids:
            raise Http404()
        url = reverse(
            'submission-inspect',
            kwargs={'submission_id': ids[0], **kwargs},
        )
        return self.redirect(url)


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
        enrollment = self.instance.get_enrollment_for(profile.user)
        if not enrollment:
            messages.warning(self.request, _("USER_NOT_ENROLLED"))
        elif enrollment.status != Enrollment.ENROLLMENT_STATUS.ACTIVE:
            status_string = Enrollment.ENROLLMENT_STATUS[enrollment.status]
            messages.warning(
                self.request,
                format_lazy(
                    _("NO_LONGER_PARTICIPATING_IN_COURSE -- {status}"),
                    status=status_string
                ),
            )
        elif enrollment.role in (Enrollment.ENROLLMENT_ROLE.TEACHER, Enrollment.ENROLLMENT_ROLE.ASSISTANT):
            messages.warning(self.request, _("USER_IS_COURSE_STAFF"))

        exercise = LearningObject.objects.find_enrollment_exercise(
            self.instance,
            profile.is_external,
        )
        if exercise:
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
                format_lazy(
                    _("ERROR_INVALID_POST_DATA -- {error}"),
                    error="\n".join(extract_form_errors(form))
                )
            )
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

    def get_common_objects(self) -> None:
        self.groups = self.instance.groups.prefetch_related(None).prefetch_related(
            Prefetch('members', UserProfile.objects.prefetch_tags(self.instance)),
        )
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


class SubmissionApprovalView(SubmissionMixin, BaseRedirectView):
    """
    A POST-only view that approves a student's late or unofficial submission
    as a normal, graded submission. The late penalty of the submission is
    removed and the submission status is changed to ready.
    """
    access_mode = ACCESS.GRADING

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        self.submission.approve_penalized_submission()
        self.submission.save()
        messages.success(self.request, format_lazy(
            _('SUBMISSION_APPROVAL_SUCCESS -- {points}, {max_points}'),
            points=self.submission.grade,
            max_points=self.submission.exercise.max_points,
        ))
        return self.redirect(self.submission.get_inspect_url())


class SubmissionApprovalByModuleView(CourseInstanceMixin, BaseRedirectView):
    """
    A POST-only view that approves a student's late or unofficial submissions
    as normal, graded submissions in a whole module or exercise.
    """
    user_kw = 'user_id'
    submission_kw = 'submission_id'
    access_mode = ACCESS.ASSISTANT

    def get_resource_objects(self):
        super().get_resource_objects()

        self.student = get_object_or_404(
            User,
            id=self.request.POST.get(self.user_kw),
        )
        self.submission = get_object_or_404(
            Submission,
            id=self.request.POST.get(self.submission_kw),
        )
        self.exercise = self.submission.exercise
        self.module = self.exercise.course_module

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        approve_scope = self.request.POST.get('approve-scope')
        approve_type = self.request.POST.get('approve-type')

        if approve_scope == 'single-exercise':
            exercise_filter = {'exercise': self.exercise}
            disallow_assistant_grading = not self.exercise.allow_assistant_grading
        else:
            exercise_filter = {'exercise__course_module': self.module}
            disallow_assistant_grading = (BaseExercise.objects
                .filter(
                    course_module=self.module,
                    allow_assistant_grading=False,
                )
                .exists())

        if self.is_assistant and disallow_assistant_grading:
            return self.permission_denied(
                message=_('SUBMISSION_APPROVAL_ASSISTANT_PERMISSION_DENIED_MSG'),
            )

        submissions = (self.student.userprofile.submissions
            .exclude_errors()
            .defer_text_fields()
            .filter(**exercise_filter)
        )
        if approve_type == 'only-late':
            submissions = submissions.filter(
                late_penalty_applied__isnull=False,
            ).exclude(
                status=Submission.STATUS.UNOFFICIAL,
            )
        elif approve_type == 'only-unofficial':
            submissions = submissions.filter(status=Submission.STATUS.UNOFFICIAL)
        else:
            # Both late and unofficial submissions.
            # Exclude normal submissions since there are usually many of those.
            submissions = submissions.filter(
                Q(late_penalty_applied__isnull=False)
                | Q(status=Submission.STATUS.UNOFFICIAL),
            )

        count = 0
        for submission in submissions:
            submission.approve_penalized_submission()
            submission.save()
            count += 1

        messages.success(self.request, ngettext(
            'SUBMISSION_APPROVAL_MULTIPLE_SUCCESS -- {count}',
            'SUBMISSION_APPROVAL_MULTIPLE_SUCCESS_PLURAL -- {count}',
            count,
            ).format(count=count),
        )
        return self.redirect(self.submission.get_inspect_url())
