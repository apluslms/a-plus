from itertools import chain

from django.http import HttpResponse
from django.contrib import messages
from django import forms
from django.utils.translation import ugettext_lazy as _, ngettext

from course.viewbase import CourseInstanceMixin, CourseInstanceBaseView
from lib.viewbase import BaseFormView, BaseRedirectView
from authorization.permissions import ACCESS
from exercise.models import BaseExercise


class ListDeviationsView(CourseInstanceBaseView):
    access_mode = ACCESS.TEACHER

    def get_common_objects(self):
        super().get_common_objects()
        self.deviations = self.get_deviations()
        self.note("deviations")


class AddDeviationsView(CourseInstanceMixin, BaseFormView):
    access_mode = ACCESS.TEACHER

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.instance
        return kwargs

    def get_success_url(self):
        if self.overlapping_deviations:
            return self.instance.get_url("deviations-override-" + self.deviation_type)
        return self.instance.get_url("deviations-list-" + self.deviation_type)

    def form_valid(self, form):
        self.update_view(form.cleaned_data, form)
        already_have_deviation = []
        deviation_exercises = form.cleaned_data["exercise"]
        for module in form.cleaned_data["module"]:
            exercises = BaseExercise.objects.filter(course_module=module)
            deviation_exercises = chain(deviation_exercises, exercises)
        for exercise in deviation_exercises:
            for profile in form.cleaned_data["submitter"]:
                if (not self.add_deviation(exercise, profile)):
                    already_have_deviation += [(exercise.id, profile.id)]

        self.overlapping_deviations = bool(already_have_deviation)

        self.update_session()
        self.request.session['already_have_deviation'] = already_have_deviation
        return super().form_valid(form)


class OverrideDeviationsView(CourseInstanceMixin, BaseFormView):
    access_mode = ACCESS.TEACHER
    # form_class is not really used, but it is required by the FormView.
    # The form contains only checkboxes and the user input is validated in
    # the form_valid method. The form HTML is manually written in the template.
    form_class = forms.Form

    def get_success_url(self):
        return self.instance.get_url("deviations-list-" + self.deviation_type)

    def get_common_objects(self):
        super().get_common_objects()
        deviation_list = []
        for e_id, s_id in self.request.session['already_have_deviation']:
            self.append_deviation(e_id, s_id, deviation_list)
        self.deviations = deviation_list
        self.note_session()
        self.note("deviations")

    def form_valid(self, form):
        deviation_list = self.request.POST.getlist('override')
        for string in deviation_list:
            try:
                e_id, s_id = string.split('-')
                e_id, s_id = int(e_id), int(s_id)
            except ValueError:
                messages.error(self.request,
                    _('Invalid exercise or submitter id: "{string}"').format(
                        string=string
                    ))
                continue
            self.update_deviations(e_id, s_id)

        self.delete_session_data()
        return super().form_valid(form)


class RemoveDeviationsView(CourseInstanceMixin, BaseRedirectView):
    access_mode = ACCESS.TEACHER
    deviation_kw = "deviation_id"

    def get_resource_objects(self):
        super().get_resource_objects()
        self.deviation = self.get_deviation()
        self.note("deviation")

    def post(self, request, *args, **kwargs):
        self.deviation.delete()
        if request.is_ajax():
            return HttpResponse(status=204)
        return self.redirect(self.instance.get_url(
            "deviations-list-" + self.deviation_type))


class RemoveManyDeviationsView(CourseInstanceMixin, BaseFormView):
    access_mode = ACCESS.TEACHER

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.instance
        return kwargs

    def get_success_url(self):
        return self.instance.get_url("deviations-list-" + self.deviation_type)

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
