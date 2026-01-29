from typing import Any, Callable, Dict, Optional

from django import forms
from django.utils.dateparse import parse_datetime
from django.http import HttpRequest, HttpResponse

from course.models import UserTag, UserTagging
from exercise.exercise_models import BaseExercise
from .forms import (
    DeadlineRuleDeviationForm,
    RemoveDeviationForm,
    MaxSubmissionRuleDeviationForm,
)
from .viewbase import (
    AddDeviationsView,
    ListDeviationsView,
    OverrideDeviationsView,
    RemoveDeviationsByIDView,
    RemoveDeviationsView,
    get_submitters,
    get_exercises,
    cleanup_dl_usertags,
)
from .models import DeadlineRuleDeviation, MaxSubmissionsRuleDeviation


class ListDeadlinesView(ListDeviationsView):
    template_name = "deviations/list_dl.html"
    deviation_model = DeadlineRuleDeviation


class AddDeadlinesView(AddDeviationsView):
    template_name = "deviations/add_dl.html"
    form_class = DeadlineRuleDeviationForm
    deviation_model = DeadlineRuleDeviation
    session_key = 'add-deviations-data-dl'

    def get_success_no_override_url(self) -> str:
        return self.instance.get_url('deviations-add-dl')

    def get_initial(self):
        initial = super().get_initial()
        if self.request.GET.get('get_module_of_exercise'):
            exercise = BaseExercise.objects.get(id=self.request.GET.get('get_module_of_exercise'))
            initial['module'] = [exercise.course_module.id]
        return initial

    def get_initial_get_param_spec(self) -> Dict[str, Optional[Callable[[str], Any]]]:
        spec = super().get_initial_get_param_spec()
        spec.update({
            "seconds": int,
            "new_date": None,
            "without_late_penalty": lambda x: x == "true",
        })
        return spec

    def serialize_session_data(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        result = super().serialize_session_data(form_data)
        result.update({
            'seconds': form_data['seconds'],
            'new_date': str(form_data['new_date']) if form_data['new_date'] else None,
            'without_late_penalty': form_data['without_late_penalty'],
            'timezone_string': form_data['timezone_string'],
        })
        return result

    def form_valid(self, form):
        timezone_string = self.request.POST.get('timezone_string')
        form.cleaned_data['timezone_string'] = timezone_string

        dl_tag, _ = UserTag.objects.get_or_create(
            course_instance=self.instance,
            name='DL',
            slug='dl',
            description="This student has deadline deviations.",
            color='#F0A8A8',
        )

        # Add the 'dl' tag to all submitters
        submitters = get_submitters(form.cleaned_data)
        for submitter in submitters:
            UserTagging.objects.get_or_create(
                tag=dl_tag,
                user=submitter,
                course_instance=self.instance,
            )
        return super().form_valid(form)


class OverrideDeadlinesView(OverrideDeviationsView):
    template_name = "deviations/override_dl.html"
    deviation_model = DeadlineRuleDeviation
    session_key = 'add-deviations-data-dl'

    def get_success_url(self) -> str:
        return self.instance.get_url('deviations-add-dl')

    def deserialize_session_data(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        result = super().deserialize_session_data(session_data)
        result.update({
            'seconds': session_data['seconds'],
            'new_date': parse_datetime(session_data['new_date']) if session_data['new_date'] else None,
            'without_late_penalty': session_data['without_late_penalty'],
            'timezone_string': session_data['timezone_string'],
        })
        return result

    def form_valid(self, form):
        timezone_string = self.request.POST.get('timezone_string')
        form.cleaned_data['timezone_string'] = timezone_string
        return super().form_valid(form)


class RemoveDeadlinesByIDView(RemoveDeviationsByIDView):
    deviation_model = DeadlineRuleDeviation

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        submitter_ids = list(self.deviation_model.objects.filter(
            id__in=request.POST.getlist("id"),
            exercise__course_module__course_instance=self.instance,
        ).values_list("submitter_id", flat=True).distinct())

        # Let parent handle deletions
        response = super().post(request, *args, **kwargs)
        cleanup_dl_usertags(self, submitter_ids)
        return response



class RemoveDeadlinesView(RemoveDeviationsView):
    template_name = "deviations/remove_dl.html"
    form_class = RemoveDeviationForm
    deviation_model = DeadlineRuleDeviation

    def form_valid(self, form: forms.BaseForm) -> HttpResponse:
        submitter_ids = list(self.deviation_model.objects.filter(
            exercise__in=get_exercises(form.cleaned_data),
            submitter__in=get_submitters(form.cleaned_data),
        ).values_list("submitter_id", flat=True).distinct())

        # Let parent handle deletions
        response = super().form_valid(form)
        cleanup_dl_usertags(self, submitter_ids)
        return response


class ListSubmissionsView(ListDeviationsView):
    template_name = "deviations/list_submissions.html"
    deviation_model = MaxSubmissionsRuleDeviation


class AddSubmissionsView(AddDeviationsView):
    template_name = "deviations/add_submissions.html"
    form_class = MaxSubmissionRuleDeviationForm
    deviation_model = MaxSubmissionsRuleDeviation
    session_key = 'add-deviations-data-submissions'

    def get_success_no_override_url(self) -> str:
        return self.instance.get_url('deviations-add-submissions')

    def serialize_session_data(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        result = super().serialize_session_data(form_data)
        result['extra_submissions'] = form_data['extra_submissions']
        return result


class OverrideSubmissionsView(OverrideDeviationsView):
    template_name = "deviations/override_submissions.html"
    deviation_model = MaxSubmissionsRuleDeviation
    session_key = 'add-deviations-data-submissions'

    def get_success_url(self) -> str:
        return self.instance.get_url('deviations-add-submissions')

    def deserialize_session_data(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        result = super().deserialize_session_data(session_data)
        result['extra_submissions'] = session_data['extra_submissions']
        return result


class RemoveSubmissionsByIDView(RemoveDeviationsByIDView):
    deviation_model = MaxSubmissionsRuleDeviation


class RemoveSubmissionsView(RemoveDeviationsView):
    template_name = "deviations/remove_submissions.html"
    form_class = RemoveDeviationForm
    deviation_model = MaxSubmissionsRuleDeviation
