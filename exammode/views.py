from django.shortcuts import redirect
from django.views import generic
from django.views.generic.edit import DeleteView, UpdateView, FormView
from django.urls import reverse
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _

from exammode.forms import ExamSessionForm
from course.viewbase import CourseInstanceMixin
from authorization.permissions import ACCESS

from lib.viewbase import BaseFormView, BaseTemplateView, BaseViewMixin
from .models import ExamSession
from exercise.views import ExerciseView


class ExamStartView(BaseTemplateView):
    access_mode = ACCESS.STUDENT
    template_name = "exammode/exam_start.html"

    def get_context_data(self, **kwargs):
        context = super(ExamStartView, self).get_context_data(**kwargs)
        context['active_exams'] = ExamSession.active_exams.get_queryset()
        context['user_exam'] = True if self.request.user.userprofile.active_exam else False
        return context

    def post(self, request, *args, **kwargs):
        session = request.user.userprofile.active_exam.exam_taken
        if not session:
            messages.error(request, _(''))
            return redirect('exam_start')
        elif 'continue' in request.POST:
            return redirect(session.get_url())
        elif 'discard' in request.POST:
            session.end_exam(request.user)
            return redirect('exam_start')


class ExamDetailView(generic.DetailView):
    model = ExamSession

    def post(self, request, *args, **kwargs):
        session = self.get_object()
        user = request.user
        if 'start-exam' in request.POST:
            if user.is_staff or not user.userprofile.active_exam:
                return redirect(session.start_exam(user))
            else:
                return redirect('exam_start')


class ExamEndView(BaseTemplateView):
    template_name = "exammode/exam_end.html"
    access_mode = ACCESS.STUDENT

    def post(self, request, *args, **kwargs):
        session = request.user.userprofile.active_exam.exam_taken
        if 'cancel' in request.POST:
            return redirect(session.get_url())
        if 'end-exam' in request.POST:
            return redirect(session.end_exam(request.user))


class ExamFinalView(BaseTemplateView):
    template_name = "exammode/exam_final.html"
    access_mode = ACCESS.STUDENT


class ExamModuleNotDefined(BaseTemplateView):
    template_name = "exammode/exam_module_not_found.html"
    access_mode = ACCESS.STUDENT


class ExamReportView(BaseTemplateView):
    template_name = "exam_report.html"
    access_mode = ACCESS.TEACHER

    def get_context_data(self, **kwargs):
        context = super(ExamReportView, self).get_context_data(**kwargs)
        print(self)
        context['active_exams'] = ExamSession.active_exams.get_queryset()
        return context


# NOTE: Without FormView the sidebar with course content etc. does not work.
# This is quite odd, since FormView is django class, and not defined in our own
# view.py or viewbase.py files.
class ExamSessionEdit(CourseInstanceMixin, UpdateView, BaseViewMixin, FormView):
    access_mode = ACCESS.TEACHER
    template_name = 'exammode/staff/edit_session_form.html'
    fields = ['name', 'exam_module', 'room']
    model = ExamSession

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        return kwargs

    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.get_object().course_instance

        self.fields['course_instance'].queryset = CourseInstance.objects.filter(
            id=instance.id)
        self.fields['exam_module'].queryset = CourseModule.objects.filter(
            course_instance=instance)

    '''

    def get_context_data(self, **kwargs):
        context = super(ExamSessionEdit, self).get_context_data(**kwargs)
        instance = self.get_object(
        ).course_instance
        context['instance'] = instance
        context['course_instance'] = instance
        return context

    def get_success_url(self):
        redirect_kwargs = {
            'course_slug': self.kwargs['course_slug'],
            'instance_slug': self.kwargs['instance_slug']
        }
        return reverse('exam-management', kwargs=redirect_kwargs)


class ExamSessionDelete(DeleteView):
    model = ExamSession

    def get_success_url(self):
        redirect_kwargs = {
            'course_slug': self.kwargs['course_slug'],
            'instance_slug': self.kwargs['instance_slug']
        }
        return reverse('exam-management', kwargs=redirect_kwargs)

    def post(self, request, *args, **kwargs):
        if "cancel" in request.POST:
            url = self.get_success_url()
            return redirect(url)
        if "confirm" in request.POST:
            return super(ExamSessionDelete, self).post(request, *args, **kwargs)


class ExamManagementView(CourseInstanceMixin, BaseFormView):
    access_mode = ACCESS.TEACHER
    form_class = ExamSessionForm
    template_name = "exammode/staff/exam_management.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['course_instance'] = self.instance
        return kwargs

    def get_common_objects(self):
        super().get_common_objects()
        self.exam_sessions = list(self.exam_sessions)
        self.note('exam_sessions')

    def get_success_url(self):
        return self.request.path_info

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _("Changes were saved succesfully."))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("Failed to save changes."))
        return super().form_invalid(form)
    '''
    def post(self, request, *args, **kwargs):
        print("posting form now")
        form = ExamSessionForm(request.POST)
        if form.is_valid:
            form.save()
        return redirect(self.request.path_info)
    '''


class ExamsStudentView(ExerciseView):
    template_name = "exammode/exam.html"
    ajax_template_name = "exammode/exam_question.html"
