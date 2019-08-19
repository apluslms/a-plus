from django.shortcuts import render, redirect
from django.views import View, generic
from django.http import HttpResponse
from django.utils import timezone

from userprofile.viewbase import UserProfileView
from course.viewbase import EnrollableViewMixin
from authorization.permissions import ACCESS

from lib.viewbase import BaseTemplateView

from .models import ExamSession, ExamAttempt

# Create your views here.


class ExamStartView(BaseTemplateView):
    access_mode = ACCESS.STUDENT
    template_name = "exammode/exam_start.html"

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get the context
        context = super(ExamStartView, self).get_context_data(**kwargs)
        # Create any data and add it to the context
        context['active_exams'] = ExamSession.active_exams.is_active()
        return context


class ExamDetailView(generic.DetailView):
    model = ExamSession

    def post(self, request, *args, **kwargs):
        session = self.get_object()
        redirect_url = session.start_exam(request.user)

        return redirect(redirect_url)
