from itertools import groupby
from typing import Iterable, List, Optional, Tuple

from django.contrib import messages
from django.db import IntegrityError
from django.db import models
from django.shortcuts import get_object_or_404
from django.utils.text import format_lazy
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

    def get_common_objects(self) -> None:
        super().get_common_objects()

        self.deviation_groups = self.get_deviation_groups()
        self.note("deviation_groups")

    def get_deviation_groups(self) -> Iterable[Tuple[List[DeadlineRuleDeviation], bool, Optional[str]]]:
        """
        Get all deviations in this course, grouped by user and module.

        Grouping condition: deviations can be grouped if the user has been
        granted the same deviation (same values for `extra_minutes` and
        `without_late_penalty`) for all exercises in the module.

        The returned tuples contain the following values:
        1. List of deviations with the same user and module.
        2. Boolean representing whether the deviations in the list can be
        displayed as a group (i.e. the grouping condition is satisfied).
        3. An id that uniquely identifies the group of deviations.
        """
        # Find the number of exercises in each module.
        exercise_counts = (
            BaseExercise.objects.filter(
                course_module__course_instance=self.instance
            )
            .order_by()
            .values('course_module_id')
            .annotate(count=models.Count('*'))
        )
        exercise_count_by_module = {row['course_module_id']: row['count'] for row in exercise_counts}

        all_deviations = (
            DeadlineRuleDeviation.objects.filter(
                exercise__course_module__course_instance=self.instance
            )
            .select_related()
            # parent is prefetched because there may be multiple ancestors, and
            # they are needed for building the deviation's URL.
            .prefetch_related('exercise__parent')
            .order_by('submitter', 'exercise__course_module')
        )

        deviation_groups = groupby(
            all_deviations,
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
                for deviation in deviations:
                    if (
                        deviation.extra_minutes != deviations[0].extra_minutes
                        or deviation.without_late_penalty != deviations[0].without_late_penalty
                    ):
                        # These values must be equal within a group.
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
                granter=self.request.user.userprofile,
                extra_minutes=minutes,
                without_late_penalty=without_late_penalty,
            )
        except IntegrityError:
            messages.warning(self.request,
                format_lazy(
                    _('DEVIATION_WARNING_DEADLINE_DEVIATION_ALREADY_FOR -- {user}, {exercise}'),
                    user=str(profile),
                    exercise=str(exercise),
                )
            )


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
