from itertools import groupby
from typing import Any, Dict, Iterable, List, Optional, Tuple, Type

from django.db import models
from django.http import HttpRequest, HttpResponse
from django.contrib import messages
from django import forms
from django.shortcuts import get_object_or_404
from django.utils.text import format_lazy
from django.utils.translation import ugettext_lazy as _, ngettext

from course.models import CourseModule
from course.viewbase import CourseInstanceMixin, CourseInstanceBaseView
from deviations.models import SubmissionRuleDeviation
from lib.viewbase import BaseFormView, BaseRedirectView
from authorization.permissions import ACCESS
from exercise.models import BaseExercise
from userprofile.models import UserProfile


class ListDeviationsView(CourseInstanceBaseView):
    access_mode = ACCESS.TEACHER
    deviation_model: Type[SubmissionRuleDeviation]

    def get_common_objects(self) -> None:
        super().get_common_objects()
        all_deviations = self.deviation_model.objects.filter(
            exercise__course_module__course_instance=self.instance
        )
        self.deviation_groups = get_deviation_groups(all_deviations)
        self.note("deviation_groups")


class AddDeviationsView(CourseInstanceMixin, BaseFormView):
    access_mode = ACCESS.TEACHER
    deviation_model: Type[SubmissionRuleDeviation]
    session_key: str

    def get_form_kwargs(self) -> Dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.instance
        return kwargs

    def form_valid(self, form: forms.BaseForm) -> HttpResponse:
        existing_deviations = get_existing_deviations(self.deviation_model, form.cleaned_data)

        if existing_deviations:
            # Some deviations already existed. Use OverrideDeviationsView to
            # confirm which ones the user wants to override. Store the form
            # values in the current session, so they can be used afterwards.
            self.success_url = self.deviation_model.get_override_url(self.instance)
            self.request.session[self.session_key] = self.serialize_session_data(form.cleaned_data)
        else:
            self.success_url = self.deviation_model.get_list_url(self.instance)
            for exercise in BaseExercise.objects.filter(
                models.Q(id__in=form.cleaned_data['exercise'])
                | models.Q(course_module__in=form.cleaned_data['module'])
            ):
                for submitter in form.cleaned_data['submitter']:
                    new_deviation = self.deviation_model(
                        exercise=exercise,
                        submitter=submitter,
                        granter=self.request.user.userprofile,
                    )
                    new_deviation.update_by_form(form.cleaned_data)
                    new_deviation.save()

        return super().form_valid(form)

    def serialize_session_data(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert input form data into serializable values that can be stored in
        the session cache.
        """
        result = {}
        for key in ('exercise', 'module', 'submitter'):
            result[key] = [i.id for i in form_data.get(key, [])]
        return result


class OverrideDeviationsView(CourseInstanceMixin, BaseFormView):
    access_mode = ACCESS.TEACHER
    # form_class is not really used, but it is required by the FormView.
    # The form contains only checkboxes and the user input is validated in
    # the form_valid method. The form HTML is manually written in the template.
    form_class = forms.Form
    deviation_model: Type[SubmissionRuleDeviation]
    session_key: str

    def get_success_url(self) -> str:
        return self.deviation_model.get_list_url(self.instance)

    def get_common_objects(self) -> None:
        super().get_common_objects()
        self.session_data = self.deserialize_session_data(self.request.session[self.session_key])
        self.existing_deviations = get_existing_deviations(self.deviation_model, self.session_data)
        self.deviation_groups = get_deviation_groups(self.existing_deviations)
        self.note("session_data", "existing_deviations", "deviation_groups")

    def form_valid(self, form: forms.BaseForm) -> HttpResponse:
        override_deviations = set()
        deviation_list = self.request.POST.getlist('override')
        for id_pair in deviation_list:
            try:
                submitter_id, exercise_id = id_pair.split('.')
                submitter_id, exercise_id = int(submitter_id), int(exercise_id)
                override_deviations.add((submitter_id, exercise_id))
            except ValueError:
                messages.error(self.request,
                    format_lazy(
                        _("INVALID_EXERCISE_OR_SUBMITTER_ID -- {id}"),
                        id=id_pair,
                    )
                )
                continue

        existing_deviations = {(d.submitter_id, d.exercise_id): d for d in self.existing_deviations}

        for exercise in BaseExercise.objects.filter(
            models.Q(id__in=self.session_data['exercise'])
            | models.Q(course_module__in=self.session_data['module'])
        ):
            for submitter in self.session_data['submitter']:
                existing_deviation = existing_deviations.get((submitter.id, exercise.id))
                if existing_deviation is not None:
                    if (submitter.id, exercise.id) in override_deviations:
                        existing_deviation.granter = self.request.user.userprofile
                        existing_deviation.update_by_form(self.session_data)
                        existing_deviation.save()
                else:
                    new_deviation = self.deviation_model(
                        exercise=exercise,
                        submitter=submitter,
                        granter=self.request.user.userprofile,
                    )
                    new_deviation.update_by_form(self.session_data)
                    new_deviation.save()

        del self.request.session[self.session_key]
        return super().form_valid(form)

    def deserialize_session_data(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert serialized session data back into its original representation.
        """
        result = {
            'exercise': BaseExercise.objects.filter(id__in=session_data.get('exercise', [])),
            'module': CourseModule.objects.filter(id__in=session_data.get('module', [])),
            'submitter': UserProfile.objects.filter(id__in=session_data.get('submitter', []))
        }
        return result


class RemoveDeviationsByIDView(CourseInstanceMixin, BaseRedirectView):
    access_mode = ACCESS.TEACHER
    deviation_model: Type[SubmissionRuleDeviation]

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        deviations = self.deviation_model.objects.filter(
            id__in=request.POST.getlist("id"),
            exercise__course_module__course_instance=self.instance,
        )
        for deviation in deviations:
            deviation.delete()
        if request.is_ajax():
            return HttpResponse(status=204)
        return self.redirect(self.deviation_model.get_list_url(self.instance))


class RemoveDeviationsView(CourseInstanceMixin, BaseFormView):
    access_mode = ACCESS.TEACHER
    deviation_model: Type[SubmissionRuleDeviation]

    def get_form_kwargs(self) -> Dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.instance
        return kwargs

    def get_success_url(self) -> str:
        return self.deviation_model.get_list_url(self.instance)

    def form_valid(self, form: forms.BaseForm) -> HttpResponse:
        number_of_removed = 0
        for deviation in get_existing_deviations(self.deviation_model, form.cleaned_data):
            deviation.delete()
            number_of_removed += 1
        if number_of_removed == 0:
            messages.warning(self.request, _("NOTHING_REMOVED"))
        else:
            message = format_lazy(
                ngettext(
                    'REMOVED_DEVIATION -- {count}',
                    'REMOVED_DEVIATIONS -- {count}',
                    number_of_removed
                ),
                count=number_of_removed,
            )
            messages.info(self.request, message)
        return super().form_valid(form)


def get_deviation_groups(
        all_deviations: models.QuerySet[SubmissionRuleDeviation],
        ) -> Iterable[Tuple[List[SubmissionRuleDeviation], bool, Optional[str]]]:
    """
    Group the deviations by user and module.

    Grouping condition: deviations can be grouped if the user has been
    granted the same deviation (based on the `is_equal` method) for all
    exercises in the module.

    The returned tuples contain the following values:
    1. List of deviations with the same user and module.
    2. Boolean representing whether the deviations in the list can be
    displayed as a group (i.e. the grouping condition is satisfied).
    3. An id that uniquely identifies the group of deviations.
    """
    # Find the number of exercises in each module.
    course_instances = all_deviations.values_list('exercise__course_module__course_instance', flat=True)
    exercise_counts = (
        BaseExercise.objects.filter(
            course_module__course_instance__in=course_instances
        )
        .order_by()
        .values('course_module_id')
        .annotate(count=models.Count('*'))
    )
    exercise_count_by_module = {row['course_module_id']: row['count'] for row in exercise_counts}

    ordered_deviations = (
        all_deviations
        .select_related()
        # parent is prefetched because there may be multiple ancestors, and
        # they are needed for building the deviation's URL.
        .prefetch_related('exercise__parent')
        .order_by('submitter', 'exercise__course_module')
    )

    deviation_groups = groupby(
        ordered_deviations,
        lambda obj: (obj.submitter, obj.exercise.course_module),
    )
    for (submitter, module), deviations_iter in deviation_groups:
        deviations = list(deviations_iter)
        can_group = True
        if len(deviations) < 2:
            # Group must have at least 2 deviations.
            can_group = False
        else:
            group_exercises = set()
            # Check that the same deviation has been granted for all exercises.
            for deviation in deviations:
                if not deviation.is_groupable(deviations[0]):
                    can_group = False
                    break
                group_exercises.add(deviation.exercise.id)
            else:
                if len(group_exercises) != exercise_count_by_module[module.id]:
                    # The number of exercises that have deviations doesn't
                    # match the number of exercises in the module, so there
                    # are some exercises that don't have a deviation.
                    can_group = False
        group_id = f"{deviations[0].submitter.id}.{module.id}" if can_group else None
        yield (deviations, can_group, group_id)


def get_existing_deviations(
        deviation_model: Type[SubmissionRuleDeviation],
        form_data: Dict[str, Any]
        ) -> models.QuerySet[SubmissionRuleDeviation]:
    """
    Get the deviations that match the input form's `exercise`, `module` and
    `submitter` fields.
    """
    return deviation_model.objects.filter(
        (
            models.Q(exercise__in=form_data.get("exercise", []))
            | models.Q(exercise__course_module__in=form_data.get("module", []))
        )
        & models.Q(submitter__in=form_data["submitter"])
    )
