from django.contrib import messages
from django import forms
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _, ngettext
from userprofile.models import UserProfile

from course.viewbase import CourseInstanceBaseView, CourseInstanceMixin
from lib.viewbase import BaseFormView, BaseRedirectView
from authorization.permissions import ACCESS
from .forms import DeadlineRuleDeviationForm, RemoveDeadlineRuleDeviationForm
from .models import DeadlineRuleDeviation
from exercise.models import BaseExercise
from itertools import chain


class OverrideDeadlinesView(CourseInstanceMixin, BaseFormView):
    access_mode = ACCESS.TEACHER
    template_name = "deviations/override.html"
    # form_class is not really used, but it is required by the FormView.
    # The form contains only checkboxes and the user input is validated in
    # the form_valid method. The form HTML is manually written in the template.
    form_class = forms.Form

    def get_success_url(self):
        return self.instance.get_url("deviations-list-dl")

    def get_common_objects(self):
        super().get_common_objects()
        deviation_list = []
        for e_id, s_id in self.request.session['already_have_deviation']:
            try:
                deviation_list.append(DeadlineRuleDeviation.objects.get(
                        exercise=BaseExercise.objects.get(id=e_id),
                        submitter=UserProfile.objects.get(id=s_id),
                        exercise__course_module__course_instance=self.instance))
            except (BaseExercise.DoesNotExist, UserProfile.DoesNotExist):
                pass # Ignore. The exercise or user was suddenly deleted.
            except DeadlineRuleDeviation.DoesNotExist:
                DeadlineRuleDeviation.objects.create(
                    exercise=BaseExercise.objects.get(id=e_id),
                    submitter=UserProfile.objects.get(id=s_id),
                    extra_minutes=self.request.session['deviations_minutes'],
                    without_late_penalty=self.request.session['without_late_penalty']
                )
        self.deviations = deviation_list
        self.without_late_penalty = self.request.session['without_late_penalty']
        self.minutes = self.request.session['deviations_minutes']
        self.note("deviations", "without_late_penalty", "minutes")

    def form_valid(self, form):

        deviation_list = self.request.POST.getlist('override')
        minutes = self.request.session['deviations_minutes']
        without_late_penalty = self.request.session['without_late_penalty']
        for string in deviation_list:
            if len(string.split('-')) != 2:
                continue
            else:
                e_id, s_id = string.split('-')
            try:
                DeadlineRuleDeviation.objects.filter(
                    exercise=BaseExercise.objects.get(id=e_id),
                    submitter=UserProfile.objects.get(id=s_id)
                ).update(
                    extra_minutes=minutes,
                    without_late_penalty=without_late_penalty
                )
            except (BaseExercise.DoesNotExist, UserProfile.DoesNotExist):
                pass

        del self.request.session['already_have_deviation']
        del self.request.session['deviations_minutes']
        del self.request.session['without_late_penalty']
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
    overlapping_deviations = False

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.instance
        return kwargs

    def get_success_url(self):
        if self.overlapping_deviations:
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
        deviation_exercises = form.cleaned_data["exercise"]
        for module in form.cleaned_data["module"]:
            exercises = BaseExercise.objects.filter(course_module=module)
            deviation_exercises = chain(deviation_exercises, exercises)
        for exercise in deviation_exercises:
            for profile in form.cleaned_data["submitter"]:
                if new_date:
                    minutes = exercise.delta_in_minutes_from_closing_to_date(
                                new_date)
                if (not self.add_deviation(exercise, profile, minutes, without_late_penalty)):
                    already_have_deviation += [(exercise.id, profile.id)]

        self.request.session['deviations_minutes'] = minutes
        self.request.session['without_late_penalty'] = without_late_penalty

        if already_have_deviation:
            self.overlapping_deviations = True
        else:
            self.overlapping_deviations = False

        self.request.session['already_have_deviation'] = already_have_deviation

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


class RemoveManyDeadlinesView(CourseInstanceMixin, BaseFormView):
    access_mode = ACCESS.TEACHER
    template_name = "deviations/remove_dl.html"
    form_class = RemoveDeadlineRuleDeviationForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.instance
        return kwargs

    def get_success_url(self):
        return self.instance.get_url("deviations-list-dl")

    def form_valid(self, form):
        number_of_removed = 0
        deviation_exercises = form.cleaned_data["exercise"]
        for module in form.cleaned_data["module"]:
            exercises = BaseExercise.objects.filter(course_module=module)
            deviation_exercises = chain(deviation_exercises, exercises)
        for exercise in deviation_exercises:
            for profile in form.cleaned_data["submitter"]:
                if (self.remove_deviation(exercise, profile)):
                    number_of_removed += 1
        if number_of_removed == 0:
            messages.warning(self.request, _("Nothing removed!"))
        else:
            message = ngettext(
                "Removed %(count)d deviation!",
                "Removed %(count)d deviations!",
                number_of_removed) % {'count': number_of_removed}
            messages.info(self.request, message)
        return super().form_valid(form)

    def remove_deviation(self, exercise, profile):
        deviation = DeadlineRuleDeviation.objects.filter(
                exercise=exercise,
                submitter=profile,
                exercise__course_module__course_instance=self.instance)
        if deviation:
            deviation.delete()
            return True
        return False
