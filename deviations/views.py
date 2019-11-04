from itertools import chain

from django.contrib import messages
from django import forms
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _, ngettext

from course.viewbase import CourseInstanceBaseView, CourseInstanceMixin
from lib.viewbase import BaseFormView, BaseRedirectView
from authorization.permissions import ACCESS
from .forms import (
    DeadlineRuleDeviationForm, RemoveDeviationForm,
    MaxSubmissionRuleDeviationForm
    )
from .models import DeadlineRuleDeviation, MaxSubmissionsRuleDeviation
from exercise.models import BaseExercise
from userprofile.models import UserProfile


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
        return self.instance.get_url("deviations-list-dl")

    def form_valid(self, form):
        minutes = form.cleaned_data["minutes"]
        new_date = form.cleaned_data["new_date"]
        if not minutes and not new_date:
            messages.warning(self.request,
                    _("You have to provide either minutes or a date in the future."))
            return super().form_valid(form)

        without_late_penalty = form.cleaned_data["without_late_penalty"]
        already_have_dl_deviation = []
        deviation_exercises = form.cleaned_data["exercise"]
        for module in form.cleaned_data["module"]:
            exercises = BaseExercise.objects.filter(course_module=module)
            deviation_exercises = chain(deviation_exercises, exercises)
        for exercise in deviation_exercises:
            for profile in form.cleaned_data["submitter"]:
                if new_date:
                    minutes = exercise.delta_in_minutes_from_closing_to_date(
                                new_date)
                if (not self.add_dl_deviation(exercise, profile, minutes, without_late_penalty)):
                    already_have_dl_deviation += [(exercise.id, profile.id)]

        self.request.session['deviations_minutes'] = minutes
        self.request.session['without_late_penalty'] = without_late_penalty

        if already_have_dl_deviation:
            self.overlapping_deviations = True
        else:
            self.overlapping_deviations = False

        self.request.session['already_have_dl_deviation'] = already_have_dl_deviation
        return super().form_valid(form)

    def add_dl_deviation(self, exercise, profile, minutes, without_late_penalty):
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


class OverrideDeadlinesView(CourseInstanceMixin, BaseFormView):
    access_mode = ACCESS.TEACHER
    template_name = "deviations/override_dl.html"
    # form_class is not really used, but it is required by the FormView.
    # The form contains only checkboxes and the user input is validated in
    # the form_valid method. The form HTML is manually written in the template.
    form_class = forms.Form

    def get_success_url(self):
        return self.instance.get_url("deviations-list-dl")

    def get_common_objects(self):
        super().get_common_objects()
        deviation_list = []
        for e_id, s_id in self.request.session['already_have_dl_deviation']:
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

        del self.request.session['already_have_dl_deviation']
        del self.request.session['deviations_minutes']
        del self.request.session['without_late_penalty']
        return super().form_valid(form)


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
        # TODO check that CSRF tokens are verified
        self.deviation.delete()
        if request.is_ajax():
            return HttpResponse(status=204)
        return self.redirect(self.instance.get_url("deviations-list-dl"))


class RemoveManyDeadlinesView(CourseInstanceMixin, BaseFormView):
    access_mode = ACCESS.TEACHER
    template_name = "deviations/remove_dl.html"
    form_class = RemoveDeviationForm

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


class ListSubmissionsView(CourseInstanceBaseView):
    access_mode = ACCESS.TEACHER
    template_name = "deviations/list_submissions.html"

    def get_common_objects(self):
        super().get_common_objects()
        self.deviations = MaxSubmissionsRuleDeviation.objects.filter(
            exercise__course_module__course_instance=self.instance)
        self.note("deviations")


class AddSubmissionsView(CourseInstanceMixin, BaseFormView):
    access_mode = ACCESS.TEACHER
    template_name = "deviations/add_submissions.html"
    form_class = MaxSubmissionRuleDeviationForm
    overlapping_deviations = False

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.instance
        return kwargs

    def get_success_url(self):
        if self.overlapping_deviations:
            return self.instance.get_url("deviations-override-submissions")
        return self.instance.get_url("deviations-list-submissions")

    def form_valid(self, form):
        bonus_submissions = form.cleaned_data["number_of_extra_submissions"]
        deviation_exercises = form.cleaned_data["exercise"]
        already_have_submission_deviation = []
        for module in form.cleaned_data["module"]:
            exercises = BaseExercise.objects.filter(course_module=module)
            deviation_exercises = chain(deviation_exercises, exercises)
        for exercise in deviation_exercises:
            for profile in form.cleaned_data["submitter"]:
                if (not self.add_submission_deviation(exercise, profile, bonus_submissions)):
                    already_have_submission_deviation += [(exercise.id, profile.id)]

        if already_have_submission_deviation:
            self.overlapping_deviations = True
        else:
            self.overlapping_deviations = False

        self.request.session['already_have_submission_deviation'] = already_have_submission_deviation
        self.request.session['number_of_extra_submissions'] = bonus_submissions
        return super().form_valid(form)

    def add_submission_deviation(self, exercise, profile, bonus_submissions):
        try:
            MaxSubmissionsRuleDeviation.objects.create(
                exercise=exercise,
                submitter=profile,
                extra_submissions=bonus_submissions,
            )
            return True
        except IntegrityError:
            return False


class OverrideSubmissionsView(CourseInstanceMixin, BaseFormView):
    access_mode = ACCESS.TEACHER
    template_name = "deviations/override_submissions.html"
    # form_class is not really used, but it is required by the FormView.
    # The form contains only checkboxes and the user input is validated in
    # the form_valid method. The form HTML is manually written in the template.
    form_class = forms.Form

    def get_success_url(self):
        return self.instance.get_url("deviations-list-submissions")

    def get_common_objects(self):
        super().get_common_objects()
        deviation_list = []
        bonus_submissions = self.request.session['number_of_extra_submissions']
        for e_id, s_id in self.request.session['already_have_submission_deviation']:
            try:
                deviation_list.append(MaxSubmissionsRuleDeviation.objects.get(
                        exercise=BaseExercise.objects.get(id=e_id),
                        submitter=UserProfile.objects.get(id=s_id),
                        exercise__course_module__course_instance=self.instance))
            except (BaseExercise.DoesNotExist, UserProfile.DoesNotExist):
                pass # Ignore. The exercise or user was suddenly deleted.
            except MaxSubmissionsRuleDeviation.DoesNotExist:
                MaxSubmissionsRuleDeviation.objects.create(
                    exercise=BaseExercise.objects.get(id=e_id),
                    submitter=UserProfile.objects.get(id=s_id),
                    extra_submissions=bonus_submissions
                )
        self.deviations = deviation_list
        self.bonus_submissions = bonus_submissions
        self.note("deviations", "bonus_submissions")

    def form_valid(self, form):

        deviation_list = self.request.POST.getlist('override')
        bonus_submissions = self.request.session['number_of_extra_submissions']
        for string in deviation_list:
            if len(string.split('-')) != 2:
                continue
            else:
                e_id, s_id = string.split('-')
            try:
                MaxSubmissionsRuleDeviation.objects.filter(
                    exercise=BaseExercise.objects.get(id=e_id),
                    submitter=UserProfile.objects.get(id=s_id)
                ).update(
                    extra_submissions=bonus_submissions
                )
            except (BaseExercise.DoesNotExist, UserProfile.DoesNotExist):
                pass

        del self.request.session['already_have_submission_deviation']
        del self.request.session['number_of_extra_submissions']
        return super().form_valid(form)


class RemoveSubmissionView(CourseInstanceMixin, BaseRedirectView):
    access_mode = ACCESS.TEACHER
    deviation_kw = "deviation_id"

    def get_resource_objects(self):
        super().get_resource_objects()
        self.deviation = get_object_or_404(
            MaxSubmissionsRuleDeviation,
            id=self._get_kwarg(self.deviation_kw),
            exercise__course_module__course_instance=self.instance,
        )
        self.note("deviation")

    def post(self, request, *args, **kwargs):
        self.deviation.delete()
        if request.is_ajax():
            return HttpResponse(status=204)
        return self.redirect(self.instance.get_url("deviations-list-submissions"))


class RemoveManySubmissionsView(CourseInstanceMixin, BaseFormView):
    access_mode = ACCESS.TEACHER
    template_name = "deviations/remove_submissions.html"
    form_class = RemoveDeviationForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.instance
        return kwargs

    def get_success_url(self):
        return self.instance.get_url("deviations-list-submissions")

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
        deviation = MaxSubmissionsRuleDeviation.objects.filter(
                exercise=exercise,
                submitter=profile,
                exercise__course_module__course_instance=self.instance)
        if deviation:
            deviation.delete()
            return True
        return False
