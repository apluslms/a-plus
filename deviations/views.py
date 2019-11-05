from django.db import IntegrityError
from django.shortcuts import get_object_or_404

from authorization.permissions import ACCESS
from .forms import (
    DeadlineRuleDeviationForm, RemoveDeviationForm,
    MaxSubmissionRuleDeviationForm
    )
from .viewbase import (
    AddDeviationsView, ListDeviationsView, OverrideDeviationsView,
    RemoveDeviationsView, RemoveManyDeviationsView)
from .models import DeadlineRuleDeviation, MaxSubmissionsRuleDeviation
from exercise.models import BaseExercise
from userprofile.models import UserProfile


class ListDeadlinesView(ListDeviationsView):
    template_name = "deviations/list_dl.html"

    def get_deviations(self):
        return DeadlineRuleDeviation.objects.filter(
            exercise__course_module__course_instance=self.instance)


class AddDeadlinesView(AddDeviationsView):
    template_name = "deviations/add_dl.html"
    form_class = DeadlineRuleDeviationForm
    overlapping_deviations = False
    deviation_type = "dl"

    def update_view(self, cleaned_data, form):
        self.without_late_penalty = cleaned_data["without_late_penalty"]
        self.minutes = cleaned_data["minutes"]
        self.new_date = cleaned_data["new_date"]

    def add_deviation(self, exercise, profile):
        minutes = self.minutes
        if self.new_date:
            minutes = exercise.delta_in_minutes_from_closing_to_date(
                        self.new_date)
        try:
            DeadlineRuleDeviation.objects.create(
                exercise=exercise,
                submitter=profile,
                extra_minutes=minutes,
                without_late_penalty=self.without_late_penalty
            )
            return True
        except IntegrityError:
            self.request.session[get_key_for_minutes(exercise.id)] = minutes
            return False

    def update_session(self):
        self.request.session['without_late_penalty'] = self.without_late_penalty


class OverrideDeadlinesView(OverrideDeviationsView):
    template_name = "deviations/override_dl.html"
    deviation_type = "dl"

    def append_deviation(self, e_id, s_id, deviation_list):
        try:
            deviation_list.append([DeadlineRuleDeviation.objects.get(
                    exercise=BaseExercise.objects.get(id=e_id),
                    submitter=UserProfile.objects.get(id=s_id),
                    exercise__course_module__course_instance=self.instance),
                    self.request.session[get_key_for_minutes(e_id)]])
        except (BaseExercise.DoesNotExist, UserProfile.DoesNotExist):
            pass # Ignore. The exercise or user was suddenly deleted.
        except DeadlineRuleDeviation.DoesNotExist:
            DeadlineRuleDeviation.objects.create(
                exercise=BaseExercise.objects.get(id=e_id),
                submitter=UserProfile.objects.get(id=s_id),
                extra_minutes=self.request.session[get_key_for_minutes(e_id)],
                without_late_penalty=self.request.session['without_late_penalty']
            )

    def note_session(self):
        self.without_late_penalty = self.request.session['without_late_penalty']
        self.note('without_late_penalty')

    def update_deviations(self, e_id, s_id):
        try:
            DeadlineRuleDeviation.objects.filter(
                exercise=BaseExercise.objects.get(id=e_id),
                submitter=UserProfile.objects.get(id=s_id)
            ).update(
                extra_minutes=self.request.session[get_key_for_minutes(e_id)],
                without_late_penalty=self.request.session['without_late_penalty']
            )
        except (BaseExercise.DoesNotExist, UserProfile.DoesNotExist):
            pass
        del self.request.session[get_key_for_minutes(e_id)]

    def delete_session_data(self):
        del self.request.session['already_have_deviation']
        del self.request.session['without_late_penalty']


class RemoveDeadlineView(RemoveDeviationsView):
    deviation_type = "dl"

    def get_deviation(self):
        return get_object_or_404(
            DeadlineRuleDeviation,
            id=self._get_kwarg(self.deviation_kw),
            exercise__course_module__course_instance=self.instance,
        )


class RemoveManyDeadlinesView(RemoveManyDeviationsView):
    template_name = "deviations/remove_dl.html"
    form_class = RemoveDeviationForm
    deviation_type = "dl"

    def remove_deviation(self, exercise, profile):
        deviation = DeadlineRuleDeviation.objects.filter(
                exercise=exercise,
                submitter=profile,
                exercise__course_module__course_instance=self.instance)
        if deviation:
            deviation.delete()
            return True
        return False


class ListSubmissionsView(ListDeviationsView):
    template_name = "deviations/list_submissions.html"

    def get_deviations(self):
        return MaxSubmissionsRuleDeviation.objects.filter(
            exercise__course_module__course_instance=self.instance)


class AddSubmissionsView(AddDeviationsView):
    template_name = "deviations/add_submissions.html"
    form_class = MaxSubmissionRuleDeviationForm
    overlapping_deviations = False
    deviation_type = "submissions"

    def update_view(self, opt_dict, form):
        self.bonus_submissions = opt_dict["number_of_extra_submissions"]

    def add_deviation(self, exercise, profile):

        try:
            MaxSubmissionsRuleDeviation.objects.create(
                exercise=exercise,
                submitter=profile,
                extra_submissions=self.bonus_submissions,
            )
            return True
        except IntegrityError:
            return False

    def update_session(self):
        self.request.session['number_of_extra_submissions'] = self.bonus_submissions


class OverrideSubmissionsView(OverrideDeviationsView):
    access_mode = ACCESS.TEACHER
    template_name = "deviations/override_submissions.html"
    deviation_type = "submissions"

    def append_deviation(self, e_id, s_id, deviation_list):
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
                extra_submissions=self.request.session['number_of_extra_submissions']
            )

    def note_session(self):
        self.bonus_submissions = self.request.session['number_of_extra_submissions']
        self.note("bonus_submissions")

    def update_deviations(self, e_id, s_id):
        try:
            MaxSubmissionsRuleDeviation.objects.filter(
                exercise=BaseExercise.objects.get(id=e_id),
                submitter=UserProfile.objects.get(id=s_id)
            ).update(
                extra_submissions=self.bonus_submissions
            )
        except (BaseExercise.DoesNotExist, UserProfile.DoesNotExist):
            pass

    def delete_session_data(self):
        del self.request.session['already_have_deviation']
        del self.request.session['number_of_extra_submissions']


class RemoveSubmissionView(RemoveDeviationsView):
    deviation_type = "submissions"

    def get_deviation(self):
        return get_object_or_404(
            MaxSubmissionsRuleDeviation,
            id=self._get_kwarg(self.deviation_kw),
            exercise__course_module__course_instance=self.instance,
            )


class RemoveManySubmissionsView(RemoveManyDeviationsView):
    template_name = "deviations/remove_submissions.html"
    form_class = RemoveDeviationForm
    deviation_type = "submissions"

    def remove_deviation(self, exercise, profile):
        deviation = MaxSubmissionsRuleDeviation.objects.filter(
                exercise=exercise,
                submitter=profile,
                exercise__course_module__course_instance=self.instance)
        if deviation:
            deviation.delete()
            return True
        return False

def get_key_for_minutes(id):
    return 'deviations_minutes' + str(id)
