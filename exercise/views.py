from typing import Any, Dict, List, Optional, Sequence, Tuple

from difflib import ndiff
from django.contrib import messages
from django.http.request import HttpRequest
from django.http.response import Http404, HttpResponse, HttpResponseNotFound
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _, get_language
from django.utils.text import format_lazy
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from django.db import DatabaseError
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from authorization.permissions import ACCESS
from course.models import CourseModule, SubmissionTag
from course.viewbase import CourseInstanceBaseView, EnrollableViewMixin
from lib.helpers import query_dict_to_list_of_tuples, safe_file_name, is_ajax
from lib.remote_page import RemotePageNotFound, request_for_response
from lib.viewbase import BaseRedirectMixin, BaseView
from userprofile.models import UserProfile
from .cache.points import ExercisePoints
from .models import BaseExercise, LearningObject, LearningObjectDisplay
from .protocol.exercise_page import ExercisePage
from .submission_models import SubmittedFile, Submission, SubmissionTagging, PendingSubmission
from .viewbase import (
    ExerciseBaseView,
    SubmissionBaseView,
    SubmissionDraftBaseView,
    SubmissionMixin,
    ExerciseModelBaseView,
    ExerciseTemplateBaseView,
)

from .exercisecollection_models import ExerciseCollection
from django.urls import reverse


class TableOfContentsView(CourseInstanceBaseView):
    template_name = "exercise/toc.html"


class ResultsView(TableOfContentsView):
    template_name = "exercise/results.html"

class SubmissionTaggingAddView(CourseInstanceBaseView):
    access_mode = ACCESS.ASSISTANT

    def post(self, request, *args, **kwargs):
        submission_id = self.kwargs['submission_id']
        subtag_id = self.kwargs['subtag_id']

        # Get the Submission and SubTag objects using these ids
        submission = Submission.objects.get(id=submission_id)
        subtag = SubmissionTag.objects.get(id=subtag_id, course_instance=self.instance)

        # Create a new SubmissionTagging object
        SubmissionTagging.objects.create(submission=submission, tag=subtag)

        # Redirect back to the previous page
        return redirect(request.META.get('HTTP_REFERER', '/'))


class SubmissionTaggingRemoveView(CourseInstanceBaseView):
    access_mode = ACCESS.ASSISTANT

    def post(self, request, *args, **kwargs):
        submission_id = self.kwargs['submission_id']
        subtag_id = self.kwargs['subtag_id']

        # Get the Submission and SubTag objects using these ids
        submission = Submission.objects.get(id=submission_id)
        subtag = SubmissionTag.objects.get(id=subtag_id, course_instance=self.instance)

        # Delete SubmissionTagging object
        SubmissionTagging.objects.filter(submission=submission, tag=subtag).delete()

        # Redirect back to the previous page
        return redirect(request.META.get('HTTP_REFERER', '/'))


class ExerciseInfoView(ExerciseBaseView):
    ajax_template_name = "exercise/_exercise_info.html"

class ExerciseView(BaseRedirectMixin, ExerciseBaseView, EnrollableViewMixin):
    template_name = "exercise/exercise.html"
    ajax_template_name = "exercise/exercise_plain.html"
    post_url_name = "exercise"
    access_mode = ACCESS.STUDENT

    # Allow form posts without the cross-site-request-forgery key.
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_access_mode(self):
        access_mode = super().get_access_mode()

        # Loosen the access mode if exercise is enrollment
        if (self.exercise.status in (
                LearningObject.STATUS.ENROLLMENT,
                LearningObject.STATUS.ENROLLMENT_EXTERNAL,
              ) and access_mode == ACCESS.STUDENT):
            access_mode = ACCESS.ENROLL

        return access_mode
    # pylint: disable-next=too-many-locals
    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        exercisecollection_data = None
        submission_allowed = False
        disable_submit = False
        should_enroll = False
        issues = []
        students = [self.profile]
        all_enroll_data = None

        if self.exercise.is_submittable:
            SUBMIT_STATUS = self.exercise.SUBMIT_STATUS
            submission_status, submission_allowed, issues, students = self.submission_check()
            disable_submit = submission_status in [
                SUBMIT_STATUS.CANNOT_ENROLL,
                SUBMIT_STATUS.NOT_ENROLLED,
            ]
            should_enroll = submission_status == SUBMIT_STATUS.NOT_ENROLLED

        if (self.exercise.status == LearningObject.STATUS.MAINTENANCE
              or self.module.status == CourseModule.STATUS.MAINTENANCE):
            if self.is_course_staff:
                issue = _('EXERCISE_IN_MAINTENANCE_AND_HIDDEN_FROM_STUDENTS')
                messages.error(request, issue)
                issues.append(issue)
            else:
                page = ExercisePage(self.exercise)
                page.content = _('EXERCISE_IN_MAINTENTANCE')
                return super().get(request, *args, page=page, students=students, **kwargs)
        elif self.exercise.status in \
                (LearningObject.STATUS.ENROLLMENT, LearningObject.STATUS.ENROLLMENT_EXTERNAL):
            # Retrieve the data of the user's latest enrollment exercise submissions
            # in case the data could be reused in this enrollment exercise.
            all_enroll_data = Submission.objects.get_combined_enrollment_submission_data(self.request.user)
            # Find the intersection of form field keys that are used by the current
            # exercise and all_enroll_data.
            # Filter all_enroll_data to only contain these keys.
            include_fields = self.exercise.get_form_spec_keys().intersection(all_enroll_data.keys())
            all_enroll_data = {key: value for key, value in all_enroll_data.items()
                               if key in include_fields}

        if hasattr(self.exercise, 'generate_table_of_contents') \
              and self.exercise.generate_table_of_contents:
            self.toc = self.content.children_hierarchy(self.exercise)
            self.note("toc")

        page = self.get_page(request, students)

        if self.profile:
            LearningObjectDisplay.objects.create(learning_object=self.exercise, profile=self.profile)

        if isinstance(self.exercise, ExerciseCollection):
            exercisecollection_data = self._load_exercisecollection(request, disable_submit)

        return super().get(request,
                           *args,
                           page=page,
                           students=students,
                           submission_allowed=submission_allowed,
                           disable_submit=disable_submit,
                           should_enroll=should_enroll,
                           issues=issues,
                           exercisecollection_data=exercisecollection_data,
                           latest_enrollment_submission_data=all_enroll_data,
                           **kwargs)

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        # Stop submit trials for e.g. chapters.
        # However, allow posts from exercises switched to maintenance status.
        if not self.exercise.is_submittable:
            return self.http_method_not_allowed(request, *args, **kwargs)

        new_submission = None
        page = ExercisePage(self.exercise)
        _submission_status, submission_allowed, _issues, students = (
            self.submission_check(request)
        )
        if submission_allowed:
            try:
                new_submission = Submission.objects.create_from_post(
                    self.exercise, students, request)
            except ValueError as error:
                messages.error(request,
                    format_lazy(
                        _('SUBMISSION_ERROR_MALFORMED_POST_DATA -- {error}'),
                        error=error,
                    )
                )
            except DatabaseError:
                messages.error(request,
                    _('ERROR_SUBMISSION_SAVING_FAILED')
                )
            else:
                # Deactivate the current draft if it exists.
                self.exercise.unset_submission_draft(self.profile)

                page = self.exercise.grade(new_submission,
                    request,
                    url_name=self.post_url_name)
                for error in page.errors:
                    messages.error(request, error)

                # Enroll after succesfull enrollment exercise.
                if (
                    self.exercise.status in (
                        LearningObject.STATUS.ENROLLMENT,
                        LearningObject.STATUS.ENROLLMENT_EXTERNAL,
                    )
                    and new_submission.status == Submission.STATUS.READY
                    and not self.is_course_staff
                ):
                    self.instance.enroll_student(self.request.user)
                    message = render_to_string(
                        'exercise/_enrollment_success.html',
                        {'instance': self.instance}
                    )
                    messages.success(request, message)

                # Redirect non AJAX normally to submission page.
                if not is_ajax(request) and "__r" not in request.GET:
                    # LTI based views require redirection to LTI specific views
                    redirect_view = kwargs.get('redirect_view')
                    return self.redirect(new_submission.get_absolute_url(view_override=redirect_view) +
                        ("?wait=1" if page.is_wait else ""))

                # "grade" returns the submission feedback page. If feedback is
                # hidden, display an ungraded page instead.
                if not self.feedback_revealed:
                    base_message = _('YOUR_ANSWER_WAS_SUBMITTED_SUCCESSFULLY')
                    messages.success(
                        request,
                        f"{base_message} {self.feedback_hidden_description}",
                    )
                    page = new_submission.load(request, feedback_revealed=False)

            # Redirect non AJAX content page request back.
            if not is_ajax(request) and "__r" in request.GET:
                return self.redirect(request.GET["__r"], backup=self.exercise);

        return self.render_to_response(self.get_context_data(
            page=page, students=students, submission=new_submission))

    def submission_check(self, request=None):
        if self.exercise.grading_mode == BaseExercise.GRADING_MODE.LAST:
            # Add warning about the grading mode.
            messages.warning(self.request, _('ONLY_YOUR_LAST_SUBMISSION_WILL_BE_GRADED'))
        if not self.profile:
            issue = _('SUBMISSION_MUST_SIGN_IN_AND_ENROLL_TO_SUBMIT_EXERCISES')
            messages.error(self.request, issue)
            return self.exercise.SUBMIT_STATUS.INVALID, False, [issue], []
        submission_status, alerts, students = (
            self.exercise.check_submission_allowed(self.profile, request)
        )

        issues = []
        for msg in alerts['error_messages']:
            issues.append(msg)
            messages.error(self.request, msg)
        for msg in alerts['warning_messages']:
            issues.append(msg)
            messages.warning(self.request, msg)
        for msg in alerts['info_messages']:
            messages.info(self.request, msg)

        submission_allowed = (
            submission_status == self.exercise.SUBMIT_STATUS.ALLOWED
        )
        return submission_status, submission_allowed, issues, students

    def get_page(self, request: HttpRequest, students: List[UserProfile]) -> ExercisePage:
        """
        Determines which page should be displayed for this exercise:
        1) If the `draft` URL parameter is `true`, and there is an active
        submission draft, return the draft page.
        2) If the `submission` URL parameter is `true`, and there is a last
        submission, return the submission page.
        3) Otherwise, return the blank exercise page.
        """
        if self.exercise.is_submittable:
            # return_draft defaults to False
            # Could be changed to True to load the draft on the standalone
            # exercise page. However, that would require extra work since the
            # data-aplus-exercise and data-aplus-quiz attributes are not
            # present on the standalone quiz page.
            return_draft = request.GET.get('draft') == 'true'
            # return_submission defaults to False
            return_submission = request.GET.get('submission') == 'true'

            # Try to load the draft page, if requested
            if return_draft and self.profile:
                draft = self.exercise.get_submission_draft(self.profile)
                if draft:
                    messages.warning(request, _('DRAFT_WARNING_REMEMBER_TO_SUBMIT'))
                    return draft.load(request)

            # Try to load the latest submission, if requested and if a draft was not found
            if return_submission and self.profile:
                submission = (
                    self.exercise.get_submissions_for_student(self.profile)
                    .order_by("-submission_time")
                    .first()
                )
                if submission:
                    if self.feedback_revealed:
                        page = ExercisePage(self.exercise)
                        page.content = submission.feedback
                        page.is_loaded = True
                        return page
                    # If feedback is not revealed, return the submission page without feedback
                    return submission.load(request, feedback_revealed=False)

        # In every other case, load a blank exercise page
        return self.exercise.load(
            request,
            students,
            url_name=self.post_url_name,
        )


    def _load_exercisecollection(self, request, submission_disabled):
        user = self.profile.user

        if not submission_disabled:
            self.exercise.check_submission(user, no_update=True)

        target_exercises = []
        target_mp = 0
        user_tp = 0
        for t_exercise in self.exercise.exercises:
            it = t_exercise.parent
            ex_url = it.url
            it = it.parent
            while it is not None:
                ex_url = it.url + '/' + ex_url
                it = it.parent

            ex_name = t_exercise.name
            for candidate in t_exercise.name.split('|'):
                if request.LANGUAGE_CODE in candidate:
                    ex_name = candidate[len('{}:'.format(request.LANGUAGE_CODE)):]

            data = {"exercise": t_exercise,
                    "url": reverse("exercise", kwargs={
                        "course_slug": t_exercise.course_module.course_instance.course.url,
                        "instance_slug": t_exercise.course_module.course_instance.url,
                        "module_slug": t_exercise.course_module.url,
                        "exercise_path": ex_url,
                    }),
                    "title": ex_name,
                    "max_points": t_exercise.max_points,
                    "user_points": ExercisePoints.get(t_exercise, request.user).official_points(),
                    }
            target_exercises.append(data)
            target_mp += data['max_points']
            user_tp += data['user_points']
        # pylint: disable=undefined-loop-variable
        title = "{}: {} - {}".format(t_exercise.course_module.course_instance.course.name,
                                     t_exercise.course_module.course_instance.instance_name,
                                     t_exercise.category.name)

        loaded_content = {
            'exercises': target_exercises,
            'title': title,
            'target_max_points': target_mp,
            'user_total_points': user_tp,
            'ec_max_points': self.exercise.max_points,
            'ec_points': ExercisePoints.get(self.exercise, request.user).points,
            }

        return loaded_content


class ExercisePlainView(ExerciseView):
    raise_exception=True
    force_ajax_template=True
    post_url_name="exercise-plain"

    # Allow form posts without the cross-site-request-forgery key.
    # Allow iframe in another domain.
    @method_decorator(csrf_exempt)
    @method_decorator(xframe_options_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


def _find_name(name: str, objects: Sequence[Dict[str, Any]]) -> Tuple[str, Optional[str]]:
    for obj in objects:
        if not name or obj['name'] == name:
            return safe_file_name(obj['name']), obj.get('content', '')
    return safe_file_name(name), None


class ExerciseModelView(ExerciseModelBaseView):
    template_name = "exercise/model.html"
    ajax_template_name = "exercise/_model_files.html"
    access_mode = ACCESS.ENROLLED

    def get_common_objects(self):
        super().get_common_objects()

        id = self.exercise.course_instance.id # pylint: disable=redefined-builtin
        self.models = []
        for url,name in self.exercise.get_models():
            try:
                response = request_for_response(url, instance_id=id)
                response.encoding = "UTF-8"
            except RemotePageNotFound:
                self.models.append({'name': name})
            else:
                self.models.append({
                    'name': name,
                    'content': response.text,
                    'html': 'text/html' in response.headers.get('Content-Type'),
                })
        self.note('models')

    def get(self, request, *args, **kwargs):
        if request.GET.get('download', False):
            requested_name, data = _find_name(request.GET.get('name', ''), self.models)
            if data is None:
                return HttpResponseNotFound(f"The file {requested_name} does not exist.")

            response = HttpResponse(data, content_type='text/plain')
            response['Content-Disposition'] = f'attachment; filename="{requested_name}"'
            return response

        return super().get(request, *args, **kwargs)

class ExerciseTemplateView(ExerciseTemplateBaseView):
    template_name = "exercise/template.html"
    ajax_template_name = "exercise/_template_files.html"
    access_mode = ACCESS.ENROLLED

    def get_common_objects(self):
        super().get_common_objects()

        id = self.exercise.course_instance.id # pylint: disable=redefined-builtin
        self.templates = []
        for url,name in self.exercise.get_templates():
            try:
                response = request_for_response(url, instance_id=id)
                response.encoding = "UTF-8"
            except RemotePageNotFound:
                self.templates.append({'name': name})
            else:
                self.templates.append({
                    'name': name,
                    'content': response.text,
                    'html': 'text/html' in response.headers.get('Content-Type'),
                })
        self.note('templates')

    def get(self, request, *args, **kwargs):
        if request.GET.get('download', False):
            requested_name, data = _find_name(request.GET.get('name', ''), self.templates)
            if data is None:
                return HttpResponseNotFound(f"The file {requested_name} does not exist.")

            response = HttpResponse(data, content_type='text/plain')
            response['Content-Disposition'] = f'attachment; filename="{requested_name}"'
            return response

        return super().get(request, *args, **kwargs)


class SubmissionView(SubmissionBaseView):
    template_name = "exercise/submission.html"
    ajax_template_name = "exercise/submission_plain.html"

    def get_common_objects(self):
        super().get_common_objects()
        self.page = { "is_wait": "wait" in self.request.GET }
        self.note("page")
        # If the submission is not in 'ready' state, check if there is a pendingSubmission
        # object for this submission and fetch the number of retries from it, so the info
        # can be displayed for the user. Also display the maximum retries from settings.
        if self.submission.status != 'ready':
            try:
                pending = PendingSubmission.objects.get(submission__id=self.submission.id)
                self.pending = { "num_retries": pending.num_retries, "max_retries": settings.SUBMISSION_RETRY_LIMIT }
                self.note("pending")
            except ObjectDoesNotExist:
                pass

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not self.feedback_revealed:
            # When feedback is delayed, show a filled but ungraded form.
            # False is passed in the allow_submit parameter to hide the submit
            # button on the submission page.
            submission_page = self.submission.load(
                request,
                allow_submit=False,
                feedback_revealed=False,
            )
            kwargs.update({'submission_page': submission_page})
        return super().get(request, *args, **kwargs)


class SubmissionPlainView(SubmissionView):
    raise_exception=True
    force_ajax_template=True

    # Allow iframe in another domain.
    @method_decorator(xframe_options_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class SubmissionPollView(SubmissionMixin, BaseView):

    def get(self, request, *args, **kwargs):
        return HttpResponse(self.submission.status, content_type="text/plain")


class SubmittedFileView(SubmissionMixin, BaseView):
    file_kw = "file_id"
    file_name_kw = "file_name"

    def get_resource_objects(self):
        super().get_resource_objects()
        file_id = self._get_kwarg(self.file_kw)
        file_name = self._get_kwarg(self.file_name_kw)
        self.file = get_object_or_404(
            SubmittedFile,
            id=file_id,
            submission=self.submission
        )
        if self.file.filename != file_name:
            raise Http404()

    def get_model_answer_file_data(self):
        file_index = None
        for i, submittable_file_info in enumerate(self.exercise.exercise_info.get('form_spec', [])):
            if submittable_file_info.get('key') == self.file.param_name:
                file_index = i
                break
        try:
            language = self.submission.lang or get_language()
            url, _ = self.exercise.get_models_by_language(language)[file_index]
            response = request_for_response(url, instance_id=self.exercise.course_instance.id)
            response.encoding = "UTF-8"
            return response.text
        except (RemotePageNotFound, IndexError, TypeError) as e:
            raise Http404() from e

    def get_compared_submission_file_data(self, submission_id: int):
        try:
            submission =  get_object_or_404(
                Submission,
                id=int(submission_id),
                exercise=self.exercise
            )
            file = get_object_or_404(
                SubmittedFile,
                param_name=self.file.param_name,
                submission=submission
            )
            with file.file_object.open() as f:
                return f.read().decode('utf-8', 'ignore')
        except ValueError as e:
            raise Http404() from e

    def get(self, request, *args, **kwargs):
        try:
            with self.file.file_object.open() as f:
                bytedata = f.read()
        except OSError:
            return HttpResponseNotFound()

        # Compare to another submission.
        compare_to = request.GET.get("compare_to", None)
        if compare_to and self.exercise.course_instance.is_course_staff(request.user):
            compared_data = (
                self.get_model_answer_file_data()
                if compare_to == "model"
                else self.get_compared_submission_file_data(compare_to)
            )
            submitted_data = bytedata.decode('utf-8', 'ignore')
            diff = ndiff(compared_data.splitlines(keepends=True), submitted_data.splitlines(keepends=True))
            diff_text = ''.join([line for line in diff if line[0] != '?'])
            bytedata = diff_text.encode('utf-8')

        # Download the file.
        if request.GET.get("download", False):
            response = HttpResponse(bytedata,
                content_type="application/octet-stream")
            response["Content-Disposition"] = 'attachment; filename="{}"'.format(self.file.filename)
            return response

        if self.file.is_passed():
            return HttpResponse(bytedata, content_type=self.file.get_mime())

        return HttpResponse(bytedata.decode('utf-8', 'ignore'),
            content_type='text/plain; charset="UTF-8"')


class SubmissionDraftView(SubmissionDraftBaseView):
    """
    A POST-only view that updates the user's existing draft or creates a new
    draft with the provided form values.
    """
    access_mode = ACCESS.ENROLLED

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """
        Updates the request user's existing draft or creates a new draft.
        """
        submission_data_list = query_dict_to_list_of_tuples(request.POST)
        self.exercise.set_submission_draft(self.profile, submission_data_list)
        # Simple OK response
        return HttpResponse()
