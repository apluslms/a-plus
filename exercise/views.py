from django.conf import settings
from django.contrib import messages
from django.http.response import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import View
from django.views.static import serve

from course.viewbase import CourseInstanceBaseView
from lib.viewbase import BaseRedirectMixin
from .presentation.summary import UserExerciseSummary
from .protocol.exercise_page import ExercisePage
from .submission_models import SubmittedFile, Submission
from .viewbase import ExerciseBaseView, SubmissionBaseView, SubmissionMixin


class ResultsView(CourseInstanceBaseView):
    template_name = "exercise/results.html"


class ExerciseInfoView(ExerciseBaseView):
    ajax_template_name = "exercise/_exercise_info.html"

    def get_common_objects(self):
        super().get_common_objects()
        self.summary = UserExerciseSummary(self.exercise, self.request.user)
        self.note("summary")


class ExerciseView(BaseRedirectMixin, ExerciseBaseView):
    template_name = "exercise/exercise.html"
    ajax_template_name = "exercise/exercise_plain.html"
    post_url_name = "exercise"

    # Allow form posts without the cross-site-request-forgery key.
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_after_new_submission(self):
        self.submissions = self.exercise.get_submissions_for_student(
            self.profile) if self.profile else []
        self.summary = UserExerciseSummary(self.exercise, self.request.user)
        self.note("submissions", "summary")

    def get(self, request, *args, **kwargs):
        self.handle()
        students = self.get_students()
        if self.exercise.is_submittable():
            self.submission_check(students)
            self.get_after_new_submission()

        if self.exercise.status == 'maintenance':
            if self.is_course_staff:
                messages.error(request,
                    _("Exercise is in maintenance and content is hidden from "
                      "students."))
            else:
                page = ExercisePage(self.exercise)
                page.content = _('Unfortunately this exercise is currently '
                                 'under maintenance.')
                return self.response(page=page, students=students)

        page = self.exercise.as_leaf_class().load(request, students,
            url_name=self.post_url_name)
        return self.response(page=page, students=students)

    def post(self, request, *args, **kwargs):
        self.handle()

        # Stop submit trials for e.g. chapters.
        # However, allow posts from exercises switched to maintenance status.
        if not self.exercise.is_submittable():
            return self.http_method_not_allowed(request, *args, **kwargs)

        students = self.get_students()
        new_submission = None
        page = ExercisePage(self.exercise)
        if self.submission_check(students):
            new_submission = Submission.objects.create_from_post(
                self.exercise, students, request)
            if new_submission:
                page = self.exercise.grade(request, new_submission,
                    url_name=self.post_url_name)

                # Redirect non AJAX normally to submission page.
                if not request.is_ajax() and "__r" not in request.GET:
                    return self.redirect(new_submission.get_absolute_url() +
                        ("?wait=1" if page.is_wait else ""))
            else:
                messages.error(request,
                    _("The submission could not be saved for some reason. "
                      "The submission was not registered."))

            # Redirect non AJAX content page request back.
            if not request.is_ajax() and "__r" in request.GET:
                return self.redirect(request.GET["__r"], backup=self.exercise);

        self.get_after_new_submission()
        return self.response(page=page, students=students,
            submission=new_submission)

    def get_students(self):
        # TODO: group support
        if self.profile:
            return (self.profile,)
        return ()

    def submission_check(self, students):
        ok, issues = self.exercise.is_submission_allowed(students)
        if len(issues) > 0:
            messages.warning(self.request, "\n".join(issues))
        return ok


class ExercisePlainView(ExerciseView):
    login_redirect=False
    force_ajax_template=True
    post_url_name="exercise-plain"

    # Allow form posts without the cross-site-request-forgery key.
    # Allow iframe in another domain.
    @method_decorator(csrf_exempt)
    @method_decorator(xframe_options_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class SubmissionView(SubmissionBaseView):
    template_name = "exercise/submission.html"
    ajax_template_name = "exercise/submission_plain.html"

    def get_common_objects(self):
        super().get_common_objects()
        self.page = { "is_wait": "wait" in self.request.GET }
        self.note("page")
        if not self.request.is_ajax():
            self.get_submissions()

    def get_submissions(self):
        if self.submission.is_submitter(self.request.user):
            profile = self.profile
        else:
            profile = self.submission.submitters.first()
        self.submissions = self.exercise.get_submissions_for_student(profile)
        self.index = len(self.submissions) - list(self.submissions).index(self.submission)
        self.summary = UserExerciseSummary(self.exercise, profile.user)
        self.note("submissions", "index", "summary")


class SubmissionPlainView(SubmissionView):
    login_redirect=False
    force_ajax_template=True

    # Allow iframe in another domain.
    @method_decorator(xframe_options_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class SubmissionPollView(SubmissionMixin, View):

    def get(self, request, *args, **kwargs):
        self.handle()
        return HttpResponse(self.submission.status, content_type="text/plain")


class SubmittedFileView(SubmissionMixin, View):
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
        self.handle()
        with open(self.file.file_object.path, "rb") as f:
            bytedata = f.read()

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
