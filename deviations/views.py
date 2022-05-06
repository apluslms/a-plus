from typing import AbstractSet, Any, Dict, Optional, Tuple

from django.db import models
from django.utils.dateparse import parse_datetime

from exercise.models import BaseExercise
from userprofile.models import UserProfile
from .forms import (
    DeadlineRuleDeviationForm,
    RemoveDeviationForm,
    MaxSubmissionRuleDeviationForm,
)
from .viewbase import (
    AddDeviationsView,
    approve_late_submissions,
    approve_unofficial_submissions,
    ListDeviationsView,
    OverrideDeviationsView,
    RemoveDeviationsByIDView,
    RemoveDeviationsView,
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

    def serialize_session_data(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        result = super().serialize_session_data(form_data)
        result.update({
            'minutes': form_data['minutes'],
            'new_date': str(form_data['new_date']) if form_data['new_date'] else None,
            'without_late_penalty': form_data['without_late_penalty'],
        })
        return result

    def approve_submissions(
            self,
            exercises: models.QuerySet[BaseExercise],
            submitters: models.QuerySet[UserProfile],
            form_data: Dict[str, Any],
            ) -> Optional[int]:
        if form_data.get('approve_late_submissions', False):
            return approve_late_submissions(
                exercises,
                submitters,
                extra_minutes=form_data.get('minutes'),#TODO int or datetime?
                new_deadline=form_data.get('new_date'),
            )
        return None


class OverrideDeadlinesView(OverrideDeviationsView):
    template_name = "deviations/override_dl.html"
    deviation_model = DeadlineRuleDeviation
    session_key = 'add-deviations-data-dl'

    def deserialize_session_data(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        result = super().deserialize_session_data(session_data)
        result.update({
            'minutes': session_data['minutes'],
            'new_date': parse_datetime(session_data['new_date']) if session_data['new_date'] else None,
            'without_late_penalty': session_data['without_late_penalty'],
        })
        return result

    def approve_submissions(
            self,
            exercises: models.QuerySet[BaseExercise],
            submitters: models.QuerySet[UserProfile],
            form_data: Dict[str, Any],
            excluded_deviations: AbstractSet[Tuple[int, int]],
            ) -> int:
        return approve_late_submissions(
            exercises,
            submitters,
            excluded_deviations=excluded_deviations,
            extra_minutes=form_data.get('minutes'),
            new_deadline=form_data.get('new_date'),
        )


class RemoveDeadlinesByIDView(RemoveDeviationsByIDView):
    deviation_model = DeadlineRuleDeviation


class RemoveDeadlinesView(RemoveDeviationsView):
    template_name = "deviations/remove_dl.html"
    form_class = RemoveDeviationForm
    deviation_model = DeadlineRuleDeviation


class ListSubmissionsView(ListDeviationsView):
    template_name = "deviations/list_submissions.html"
    deviation_model = MaxSubmissionsRuleDeviation


class AddSubmissionsView(AddDeviationsView):
    template_name = "deviations/add_submissions.html"
    form_class = MaxSubmissionRuleDeviationForm
    deviation_model = MaxSubmissionsRuleDeviation
    session_key = 'add-deviations-data-submissions'

    def serialize_session_data(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        result = super().serialize_session_data(form_data)
        result['extra_submissions'] = form_data['extra_submissions']
        return result

    def approve_submissions(
            self,
            exercises: models.QuerySet[BaseExercise],
            submitters: models.QuerySet[UserProfile],
            form_data: Dict[str, Any],
            ) -> Optional[int]:
        if form_data.get('approve_unofficial_submissions', False):
            return approve_unofficial_submissions(
                exercises,
                submitters,
                extra_submissions=form_data['extra_submissions'],
            )
        return None


class OverrideSubmissionsView(OverrideDeviationsView):
    template_name = "deviations/override_submissions.html"
    deviation_model = MaxSubmissionsRuleDeviation
    session_key = 'add-deviations-data-submissions'

    def deserialize_session_data(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        result = super().deserialize_session_data(session_data)
        result['extra_submissions'] = session_data['extra_submissions']
        return result

    def approve_submissions(
            self,
            exercises: models.QuerySet[BaseExercise],
            submitters: models.QuerySet[UserProfile],
            form_data: Dict[str, Any],
            excluded_deviations: AbstractSet[Tuple[int, int]],
            ) -> int:
        return approve_unofficial_submissions(
            exercises,
            submitters,
            excluded_deviations=excluded_deviations,
            extra_submissions=form_data['extra_submissions'],
        )


class RemoveSubmissionsByIDView(RemoveDeviationsByIDView):
    deviation_model = MaxSubmissionsRuleDeviation


class RemoveSubmissionsView(RemoveDeviationsView):
    template_name = "deviations/remove_submissions.html"
    form_class = RemoveDeviationForm
    deviation_model = MaxSubmissionsRuleDeviation
