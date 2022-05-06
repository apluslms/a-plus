import datetime
from itertools import groupby
from typing import AbstractSet, Any, Dict, Iterable, List, Optional, Tuple, Type

from django.db import models
from django.http import HttpRequest, HttpResponse
from django.contrib import messages
from django import forms
from django.utils.text import format_lazy
from django.utils.translation import ugettext_lazy as _, ngettext

from course.models import CourseModule, UserTag
from course.viewbase import CourseInstanceMixin, CourseInstanceBaseView
from deviations.models import SubmissionRuleDeviation
from lib.viewbase import BaseFormView, BaseRedirectView
from authorization.permissions import ACCESS
from exercise.models import BaseExercise, Submission
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
        exercises = get_exercises(form.cleaned_data)
        submitters = get_submitters(form.cleaned_data)
        existing_deviations = self.deviation_model.objects.filter(
            exercise__in=exercises,
            submitter__in=submitters,
        )

        if existing_deviations:
            # Some deviations already existed. Use OverrideDeviationsView to
            # confirm which ones the user wants to override. Store the form
            # values in the current session, so they can be used afterwards.
            self.success_url = self.deviation_model.get_override_url(self.instance)
            self.request.session[self.session_key] = self.serialize_session_data(form.cleaned_data)
        else:
            self.success_url = self.deviation_model.get_list_url(self.instance)
            for exercise in exercises:
                for submitter in submitters:
                    new_deviation = self.deviation_model(
                        exercise=exercise,
                        submitter=submitter,
                        granter=self.request.user.userprofile,
                    )
                    new_deviation.update_by_form(form.cleaned_data)
                    new_deviation.save()
            submission_count = self.approve_submissions(
                exercises,
                submitters,
                form.cleaned_data,
            )#TODO

        return super().form_valid(form)

    def serialize_session_data(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert input form data into serializable values that can be stored in
        the session cache.
        """
        result = {}
        for key in ('exercise', 'module', 'submitter', 'submitter_tag'):
            result[key] = [i.id for i in form_data.get(key, [])]
        return result

    def approve_submissions(
            self,
            exercises: models.QuerySet[BaseExercise],
            submitters: models.QuerySet[UserProfile],
            form_data: Dict[str, Any],
            ) -> Optional[int]:
        """Approve existing late and/or unofficial submissions
        that are covered by the new deviations.

        If the form_data disables the approval, then no submissions are changed
        and this method returns None.
        Otherwise, return the number of approved submissions.
        """
        raise NotImplementedError("Child classes must override the method approve_submissions().")


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
        self.exercises = get_exercises(self.session_data)
        self.submitters = get_submitters(self.session_data)
        self.existing_deviations = self.deviation_model.objects.filter(
            exercise__in=self.exercises,
            submitter__in=self.submitters,
        )
        self.deviation_groups = get_deviation_groups(self.existing_deviations)
        self.note("session_data", "exercises", "submitters", "existing_deviations", "deviation_groups")

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

        excluded_deviations = set()
        for exercise in self.exercises:
            for submitter in self.submitters:
                deviation_pair = (submitter.id, exercise.id)
                existing_deviation = existing_deviations.get(deviation_pair)
                if existing_deviation is not None:
                    if deviation_pair in override_deviations:
                        existing_deviation.granter = self.request.user.userprofile
                        existing_deviation.update_by_form(self.session_data)
                        existing_deviation.save()
                    else:
                        excluded_deviations.add(deviation_pair)
                else:
                    new_deviation = self.deviation_model(
                        exercise=exercise,
                        submitter=submitter,
                        granter=self.request.user.userprofile,
                    )
                    new_deviation.update_by_form(self.session_data)
                    new_deviation.save()

        del self.request.session[self.session_key]
        #TODO approve late/unofficial submissions
        submission_count = self.approve_submissions(
            self.exercises,
            self.submitters,
            self.session_data,
            excluded_deviations,
        )
        return super().form_valid(form)

    def deserialize_session_data(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert serialized session data back into its original representation.
        """
        result = {
            'exercise': BaseExercise.objects.filter(id__in=session_data.get('exercise', [])),
            'module': CourseModule.objects.filter(id__in=session_data.get('module', [])),
            'submitter': UserProfile.objects.filter(id__in=session_data.get('submitter', [])),
            'submitter_tag': UserTag.objects.filter(id__in=session_data.get('submitter_tag', [])),
        }
        return result

    def approve_submissions(
            self,
            exercises: models.QuerySet[BaseExercise],
            submitters: models.QuerySet[UserProfile],
            form_data: Dict[str, Any],
            excluded_deviations: AbstractSet[Tuple[int, int]],
            ) -> int:
        """Approve existing late and/or unofficial submissions
        that are covered by the new deviations.

        Return the number of approved submissions.
        """
        raise NotImplementedError("Child classes must override the method approve_submissions().")


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
        deviations = self.deviation_model.objects.filter(
            exercise__in=get_exercises(form.cleaned_data),
            submitter__in=get_submitters(form.cleaned_data),
        )
        for deviation in deviations:
            deviation.delete()
            number_of_removed += 1
        if number_of_removed == 0:
            messages.warning(self.request, _("NOTHING_REMOVED"))
        else:
            message = format_lazy(#TODO the string is not lazy
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
    course_instances = (
        all_deviations
        .values_list('exercise__course_module__course_instance', flat=True)
        .distinct()
    )
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
        .select_related(
            'submitter', 'submitter__user',
            'granter', 'granter__user',
            'exercise', 'exercise__course_module',
        )
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


def get_exercises(form_data: Dict[str, Any]) -> models.QuerySet[BaseExercise]:
    """
    Get the exercises that match the input form's `exercise` and `module`
    fields.
    """
    return BaseExercise.objects.filter(
        models.Q(id__in=form_data.get('exercise', []))
        | models.Q(course_module__in=form_data.get('module', []))
    )


def get_submitters(form_data: Dict[str, Any]) -> models.QuerySet[UserProfile]:
    """
    Get the submitters that match the input form's `submitter` and
    `submitter_tag` fields.
    """
    return UserProfile.objects.filter(
        models.Q(id__in=form_data.get('submitter', []))
        | models.Q(taggings__tag__in=form_data.get('submitter_tag', []))
    ).distinct()


def approve_late_submissions(
        exercises: models.QuerySet[BaseExercise],
        submitters: models.QuerySet[UserProfile],
        excluded_deviations: Optional[AbstractSet[Tuple[int, int]]] = None,
        extra_minutes: Optional[int] = None,
        new_deadline: Optional[datetime.datetime] = None,
        ) -> int:
    exercises_by_module = {}
    for exercise in exercises:
        exercises_by_module.setdefault(exercise.course_module_id, []).append(exercise)

    for module_id, exercise_list in exercises_by_module.items():
        if extra_minutes is not None:
            dl = exercise_list[0].course_module.closing_time + datetime.timedelta(minutes=extra_minutes)
        else:
            dl = new_deadline
        submissions = (Submission.objects
            .exclude_errors()
            .defer_text_fields()
            .filter(
                # Late submissions do not have any late penalty when late submissions are disallowed,
                # but unofficial submissions are allowed.
                # The submission becomes then unofficial without any late penalty.
                # Note: the exercise max_submissions limit is not checked here.
                # Some of the unofficial submissions may have exceeded the submission attempt limit.
                # Those submissions are approved here as well with the assumption that
                # the teacher intended that when he/she added new deadline deviations.
                models.Q(status=Submission.STATUS.UNOFFICIAL) | models.Q(late_penalty_applied__isnull=False),
                exercise__in=exercise_list,
                submitters__in=submitters,
                submission_time__lte=dl,
            ))
        submission_count = 0
        for submission in submissions:
            may_approve = True
            for submitter in submission.submitters.all():
                if excluded_deviations and (submitter.id, submission.exercise_id) in excluded_deviations:
                    may_approve = False
                    break
            if may_approve:
                submission.approve_penalized_submission()
                submission.save()
                submission_count += 1

    return submission_count


def approve_unofficial_submissions(
        exercises: models.QuerySet[BaseExercise],
        submitters: models.QuerySet[UserProfile],
        excluded_deviations: Optional[AbstractSet[Tuple[int, int]]] = None,
        extra_submissions: int = 0,
        ) -> int:
    #TODO fix this function
    # Fetch submissions that exceeded the max submissions limit of the exercise and have status UNOFFICIAL.
    # submissions = (Submission.objects
    #     .exclude_errors()
    #     .defer_text_fields()
    #     .filter(
    #         exercise__in=exercises,
    #         submitters__in=submitters,
    #     )
    #     .annotate(rank=models.Window(#Window disallowed in filter()
    #         DenseRank(),
    #         partition_by=[models.F('exercise'), models.F('submitters')],
    #         order_by=models.F('submission_time').asc(),
    #     ))
    #     .filter(
    #         status=Submission.STATUS.UNOFFICIAL,
    #         rank__gt=models.F('exercise__max_submissions'),
    #         rank__lte=models.F('exercise__max_submissions') + extra_submissions,
    #         #exercise__in=exercises,
    #         #submitters__in=submitters,
    #     )
    #     .order_by('exercise', 'submitters', 'submission_time')
    # )

    submission_counts = (Submission.objects
        .filter(
            exercise__in=exercises,
            submitters__in=submitters,
        )
        .values(
            'exercise',
            'submitters',
        )
        .annotate(
            count=models.Count('id'),
            max_submissions=models.F('exercise__max_submissions'),
        )
        .order_by()
    )
    exercise_submitter_pairs = set()
    for c in submission_counts:
        if c['count'] > c['max_submissions']:
            exercise_submitter_pairs.add((c['exercise'], c['submitters']))
    # fetch submissions for exercise_submitter_pairs and check if some submissions should be approved
    # (over max submissions and within extra submissions, status unofficial)

    submissions = (Submission.objects
        .exclude_errors()
        .defer_text_fields()
        .filter(
            exercise__in=exercises,
            submitters__in=submitters,
        )
        .order_by('exercise', 'submitters', 'submission_time')
    )
    #TODO itertools groupby ??
    submission_count = 0
    for submission in submissions:
        # groupby? get one student's submissions in one exercise
        # count the number of submissions and approve unofficial submissions above the exercise.max_submissions
        # (extra_submissions define how many are approved)
        submission_count += 1

    ######################################### old below
    submission_count = 0
    for submission in submissions:
        may_approve = True
        for submitter in submission.submitters.all():
            if excluded_deviations and (submitter.id, submission.exercise_id) in excluded_deviations:
                may_approve = False
                break
        if may_approve:
            submission.approve_penalized_submission()
            submission.save()
            submission_count += 1

    return submission_count
