from django.shortcuts import render
from django.views import View, generic
from django.http import HttpResponse

from userprofile.viewbase import UserProfileView
from course.viewbase import EnrollableViewMixin
from authorization.permissions import ACCESS

from lib.viewbase import BaseTemplateView

from .models import ExamSession

# Create your views here.


class ExamStartView(BaseTemplateView):
    access_mode = ACCESS.STUDENT
    template_name = "exammode/exam_start.html"

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get the context
        context = super(ExamStartView, self).get_context_data(**kwargs)
        # Create any data and add it to the context
        #context['active_exams'] = ExamSession.active_exams.all()
        context['active_exams'] = ExamSession.active_exams.is_active()
        return context

    #queryset = ExamSession.active_exams.all()
    queryset = ExamSession.active_exams.is_active()


class ExamDetailView(generic.DetailView):
    #access_mode = ACCESS.STUDENT
    #template_name = "exammode/exam_details.html"
    model = ExamSession
