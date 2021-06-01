from django.contrib import messages
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from course.viewbase import CourseInstanceBaseView, CourseInstanceMixin
from lib.viewbase import BaseFormView, BaseRedirectView
from authorization.permissions import ACCESS
from .forms import DeadlineRuleDeviationForm
from .models import DeadlineRuleDeviation
from exercise.models import BaseExercise


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

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.instance
        return kwargs

    def get_success_url(self):
        return self.instance.get_url("deviations-list-dl")

    def form_valid(self, form):
        minutes = form.cleaned_data["minutes"]
        new_date = form.cleaned_data["new_date"]
        if not minutes and not new_date:
            messages.warning(self.request,
                    _('DEVIATION_WARNING_MUST_PROVIDE_MINUTES_OR_FUTURE_DATE'))
            return super().form_valid(form)

        without_late_penalty = form.cleaned_data["without_late_penalty"]
        for profile in form.cleaned_data["submitter"]:
            for module in form.cleaned_data["module"]:
                exercises = BaseExercise.objects.filter(
                    course_module = module
                )
                for exercise in exercises:
                    if new_date:
                        minutes = exercise.delta_in_minutes_from_closing_to_date(
                                new_date)
                    self.add_deviation(
                        exercise, profile, minutes, without_late_penalty)

            for exercise in form.cleaned_data["exercise"]:
                if new_date:
                    minutes = exercise.delta_in_minutes_from_closing_to_date(
                                new_date)
                self.add_deviation(
                    exercise, profile, minutes, without_late_penalty)
        return super().form_valid(form)

    def add_deviation(self, exercise, profile, minutes, without_late_penalty):
        try:
            deviation = DeadlineRuleDeviation.objects.create(
                exercise=exercise,
                submitter=profile,
                extra_minutes=minutes,
                without_late_penalty=without_late_penalty,
            )
        except IntegrityError:
            messages.warning(self.request,
                _('DEVIATION_WARNING_DEADLINE_DEVIATION_ALREADY_FOR -- {user}, {exercise}').format(
                    user=str(profile), exercise=str(exercise)))


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
