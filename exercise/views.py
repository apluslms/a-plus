from django.conf import settings
from django.contrib import messages
from django.core.exceptions import MultipleObjectsReturned, PermissionDenied
from django.http.response import Http404, HttpResponse, HttpResponseNotFound
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.utils.text import format_lazy
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from django.views.static import serve
from django.db import DatabaseError

from authorization.permissions import ACCESS
from course.models import CourseModule
from course.viewbase import CourseInstanceBaseView, EnrollableViewMixin
from lib.remote_page import RemotePageNotFound, request_for_response
from lib.viewbase import BaseRedirectMixin, BaseView
from .models import LearningObject, LearningObjectDisplay
from .protocol.exercise_page import ExercisePage
from .submission_models import SubmittedFile, Submission
from .viewbase import ExerciseBaseView, SubmissionBaseView, SubmissionMixin, ExerciseModelBaseView, ExerciseTemplateBaseView

from .exercisecollection_models import ExerciseCollection
from .exercise_summary import UserExerciseSummary
from django.urls import reverse


class TableOfContentsView(CourseInstanceBaseView):
    template_name = "exercise/toc.html"


class ResultsView(TableOfContentsView):
    template_name = "exercise/results.html"


class ExerciseInfoView(ExerciseBaseView):
    ajax_template_name = "exercise/_exercise_info.html"

    def get_common_objects(self):
        super().get_common_objects()
        self.get_summary_submissions()


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

    def get(self, request, *args, **kwargs):
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
            self.get_summary_submissions()
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

        page = self.exercise.as_leaf_class().load(request, students,
            url_name=self.post_url_name)

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

    def post(self, request, *args, **kwargs):
        # Stop submit trials for e.g. chapters.
        # However, allow posts from exercises switched to maintenance status.
        if not self.exercise.is_submittable:
            return self.http_method_not_allowed(request, *args, **kwargs)

        new_submission = None
        page = ExercisePage(self.exercise)
        submission_status, submission_allowed, issues, students = (
            self.submission_check(True, request)
        )
        if submission_allowed:
            try:
                new_submission = Submission.objects.create_from_post(
                    self.exercise, students, request)
            except ValueError as error:
                messages.error(request,
                    format_lazy(
                    _('SUBMISSION_ERROR_MALFORMED_POST_DATA -- {error}'),
                    error=error
                    )
                )
            except DatabaseError:
                messages.error(request,
                    _('ERROR_SUBMISSION_SAVING_FAILED')
                )
            else:
                page = self.exercise.grade(request, new_submission,
                    url_name=self.post_url_name)
                for error in page.errors:
                    messages.error(request, error)

                # Enroll after succesfull enrollment exercise.
                if self.exercise.status in (
                    LearningObject.STATUS.ENROLLMENT,
                    LearningObject.STATUS.ENROLLMENT_EXTERNAL,
                ) and new_submission.status == Submission.STATUS.READY:
                    self.instance.enroll_student(self.request.user)
                    message = render_to_string(
                        'exercise/_enrollment_success.html',
                        {'instance': self.instance}
                    )
                    messages.success(request, message)

                # Redirect non AJAX normally to submission page.
                if not request.is_ajax() and "__r" not in request.GET:
                    return self.redirect(new_submission.get_absolute_url() +
                        ("?wait=1" if page.is_wait else ""))

            # Redirect non AJAX content page request back.
            if not request.is_ajax() and "__r" in request.GET:
                return self.redirect(request.GET["__r"], backup=self.exercise);

        self.get_summary_submissions()
        return self.render_to_response(self.get_context_data(
            page=page, students=students, submission=new_submission))

    def submission_check(self, error=False, request=None):
        if not self.profile:
            issue = _('SUBMISSION_MUST_SIGN_IN_AND_ENROLL_TO_SUBMIT_EXERCISES')
            messages.error(self.request, issue)
            return self.exercise.SUBMIT_STATUS.INVALID, False, [issue], []
        submission_status, issues, students = (
            self.exercise.check_submission_allowed(self.profile, request)
        )
        if len(issues) > 0:
            if error:
                messages.error(self.request, "\n".join(issues))
            else:
                messages.warning(self.request, "\n".join(issues))
        submission_allowed = (
            submission_status == self.exercise.SUBMIT_STATUS.ALLOWED
        )
        return submission_status, submission_allowed, issues, students


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
                    "user_points": UserExerciseSummary(t_exercise, request.user).get_points(),
                    }
            target_exercises.append(data)
            target_mp += data['max_points']
            user_tp += data['user_points']

        title = "{}: {} - {}".format(t_exercise.course_module.course_instance.course.name,
                                     t_exercise.course_module.course_instance.instance_name,
                                     t_exercise.category.name)

        loaded_content = {
            'exercises': target_exercises,
            'title': title,
            'target_max_points': target_mp,
            'user_total_points': user_tp,
            'ec_max_points': self.exercise.max_points,
            'ec_points': UserExerciseSummary(self.exercise, request.user).best_submission.grade,
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


class ExerciseModelView(ExerciseModelBaseView):
    template_name = "exercise/model.html"
    ajax_template_name = "exercise/_model_files.html"
    access_mode = ACCESS.ENROLLED

    def get_common_objects(self):
        super().get_common_objects()
        self.get_summary_submissions()
        self.models = []
        for url,name in self.exercise.get_models():
            try:
                response = request_for_response(url)
            except RemotePageNotFound:
                self.models.append({'name': name})
            else:
                self.models.append({
                    'name': name,
                    'content': response.text,
                    'html': 'text/html' in response.headers.get('Content-Type'),
                })
        self.note('models')


class ExerciseTemplateView(ExerciseTemplateBaseView):
    template_name = "exercise/template.html"
    ajax_template_name = "exercise/_template_files.html"
    access_mode = ACCESS.ENROLLED

    def get_common_objects(self):
        super().get_common_objects()
        self.get_summary_submissions()
        self.templates = []
        for url,name in self.exercise.get_templates():
            try:
                response = request_for_response(url)
            except RemotePageNotFound as error:
                self.templates.append({'name': name})
            else:
                self.templates.append({
                    'name': name,
                    'content': response.text,
                    'html': 'text/html' in response.headers.get('Content-Type'),
                })
        self.note('templates')


class SubmissionView(SubmissionBaseView):
    template_name = "exercise/submission.html"
    ajax_template_name = "exercise/submission_plain.html"

    def get_common_objects(self):
        super().get_common_objects()
        self.page = { "is_wait": "wait" in self.request.GET }
        self.note("page")
        #if not self.request.is_ajax():
        self.get_summary_submissions()


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

    def get(self, request, *args, **kwargs):
        try:
            with self.file.file_object.open() as f:
                bytedata = f.read()
        except OSError:
            return HttpResponseNotFound()

        # Download the file.
        if request.GET.get("download", False):
            response = HttpResponse(bytedata,
                content_type="application/octet-stream")
            response["Content-Disposition"] = 'attachment; filename="{}"'\
                .format(self.file.filename)
            return response

        if self.file.is_passed():
            return HttpResponse(bytedata, content_type=self.file.get_mime())

        return HttpResponse(bytedata.decode('utf-8', 'ignore'),
            content_type='text/plain; charset="UTF-8"')
