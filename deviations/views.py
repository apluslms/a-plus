from django.contrib import messages
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _
from userprofile.models import UserProfile

from course.viewbase import CourseInstanceBaseView, CourseInstanceMixin
from lib.viewbase import BaseFormView, BaseRedirectView
from authorization.permissions import ACCESS
from .forms import DeadlineRuleDeviationForm
from .models import DeadlineRuleDeviation
from exercise.models import BaseExercise
from itertools import chain


class OverrideDeadlinesView(CourseInstanceMixin, BaseFormView):
    access_mode = ACCESS.TEACHER
    template_name = "deviations/override.html"
    form_class = DeadlineRuleDeviationForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.instance
        return kwargs

    def get_success_url(self):
        return self.instance.get_url("deviations-list-dl")

    def get_common_objects(self):
        super().get_common_objects()
        deviation_list = []
        for e, s in self.request.session['already_have_deviation']:
            deviation_list += [DeadlineRuleDeviation.objects.get(
                    exercise=BaseExercise.objects.get(id=e),
                    submitter=UserProfile.objects.get(id=s),
                    exercise__course_module__course_instance=self.instance)]

        self.deviations = deviation_list
        self.without_late_penalty = self.request.session['without_late_penalty']
        self.minutes = self.request.session['minutes']
        self.note("deviations", "without_late_penalty", "minutes")

    def form_valid(self, form):

        deviation_list = self.request.POST.getlist('override')
        minutes = self.request.session['minutes']
        without_late_penalty = self.request.session['without_late_penalty']
        for string in deviation_list:
            e, s = string.split('-')
            DeadlineRuleDeviation.objects.filter(
                exercise=BaseExercise.objects.get(id=e),
                submitter=UserProfile.objects.get(id=s)).update(
                extra_minutes=minutes,
                without_late_penalty=without_late_penalty)

        del self.request.session['already_have_deviation']
        return super().form_valid(form)


class ListDeadlinesView(CourseInstanceBaseView):
    access_mode = ACCESS.TEACHER
    template_name = "deviations/list_dl.html"

    def get_common_objects(self):
        super().get_common_objects()
        self.deviations = DeadlineRuleDeviation.objects.filter(
            exercise__course_module__course_instance=self.instance)
        self.note("deviations")


class AddDeadlinesView(CourseInstanceMixin, BaseFormView):
    access_mode = ACCESS.TEACHER
    template_name = "deviations/add_dl.html"
    form_class = DeadlineRuleDeviationForm
    already_have_deviation = []

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.instance
        return kwargs

    def get_success_url(self):
        if self.already_have_deviation:
            return self.instance.get_url("deviations-override-dl")
        else:
            return self.instance.get_url("deviations-list-dl")

    def form_valid(self, form):
        minutes = form.cleaned_data["minutes"]
        new_date = form.cleaned_data["new_date"]
        if not minutes and not new_date:
            messages.warning(self.request,
                    _("You have to provide either minutes or a date in the future."))
            return super().form_valid(form)

        without_late_penalty = form.cleaned_data["without_late_penalty"]
        already_have_deviation = []
        for profile in form.cleaned_data["submitter"]:
            deviation_exercises = form.cleaned_data["exercise"]
            for module in form.cleaned_data["module"]:
                exercises = BaseExercise.objects.filter(course_module=module)
                deviation_exercises = chain(deviation_exercises, exercises)
            for exercise in deviation_exercises:
                if new_date:
                    minutes = exercise.delta_in_minutes_from_closing_to_date(
                                new_date)
                if (not self.add_deviation(exercise, profile, minutes, without_late_penalty)):
                    already_have_deviation += [(exercise.id, profile.id)]

        self.request.session['minutes'] = minutes
        self.request.session['without_late_penalty'] = without_late_penalty

        if already_have_deviation:
            self.already_have_deviation = True
        else:
            self.already_have_deviation = False

        self.request.session['already_have_deviation'] = already_have_deviation
# show the teacher the exercises that already have the deviation and
# let them choose whether to override them or discard the changes
#            for deviation in chosen_deviations:
#                self.remove_deviation(deviation[0], deviation[1])
#                self.add_deviation(deviation[0], deviation[1], minutes, without_late_penalty)
        return super().form_valid(form)

    def add_deviation(self, exercise, profile, minutes, without_late_penalty):
        try:
            DeadlineRuleDeviation.objects.create(
                exercise=exercise,
                submitter=profile,
                extra_minutes=minutes,
                without_late_penalty=without_late_penalty,
            )
            return True
        except IntegrityError:
            return False


class RemoveDeadlineView(CourseInstanceMixin, BaseRedirectView):
    access_mode = ACCESS.TEACHER
    deviation_kw = "deviation_id"

    def get_resource_objects(self):
        super().get_resource_objects()
        self.deviation = get_object_or_404(
            DeadlineRuleDeviation,
            id=self._get_kwarg(self.deviation_kw),
            exercise__course_module__course_instance=self.instance,
        )
        self.note("deviation")

    def post(self, request, *args, **kwargs):
        self.deviation.delete()
        return self.redirect(self.instance.get_url("deviations-list-dl"))
