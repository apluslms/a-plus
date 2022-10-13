from typing import Any

from django import forms
from django.contrib.auth.models import User # pylint: disable=imported-auth-user
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from aplus.api import api_reverse
from exercise.models import Submission
from lib.fields import UsersSearchSelectField
from userprofile.models import UserProfile


class SubmissionCallbackForm(forms.Form):
    """
    Parses and validates the grading callback request.
    """
    points = forms.IntegerField(min_value=0)
    max_points = forms.IntegerField(min_value=0, required=False)
    feedback = forms.CharField(required=False)
    notify = forms.CharField(required=False)
    grading_payload = forms.CharField(required=False)
    error = forms.BooleanField(required=False)

    def clean(self):
        points      = self.cleaned_data.get("points")
        max_points  = self.cleaned_data.get("max_points", 0)
        if points and max_points:
            if points > max_points:
                raise forms.ValidationError(
                    _('SUBMISSION_ERROR_POINTS_GREATER_THAN_MAX_POINTS'))
            if points < 0:
                raise forms.ValidationError(
                    _('SUBMISSION_ERROR_POINTS_LOWER_THAN_ZERO'))
        return self.cleaned_data


class SubmissionReviewForm(forms.Form):

    points = forms.IntegerField(
        min_value=0,
        label=_('LABEL_POINTS'),
        help_text=_('SUBMISSION_REVIEW_POINTS_OVERRIDE_HELPTEXT'),
    )
    mark_as_final = forms.BooleanField(
        required=False,
        label=_('LABEL_MARK_AS_FINAL'),
        help_text=_('SUBMISSION_REVIEW_MARK_AS_FINAL_HELPTEXT'),
    )
    assistant_feedback = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={ 'rows': None, 'cols': None }),
        label=_('LABEL_STAFF_FEEDBACK'),
        help_text=_('SUBMISSION_REVIEW_ASSISTANT_FEEDBACK_HELPTEXT'),
    )
    feedback = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={ 'rows': None, 'cols': None }),
        label=_('GRADER_FEEDBACK'),
        help_text=_('SUBMISSION_REVIEW_FEEDBACK_OVERRIDE_HELPTEXT'),
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.exercise = kwargs.pop('exercise')
        help_texts_to_tooltips = kwargs.pop('help_texts_to_tooltips', False)
        super().__init__(*args, **kwargs)

        if help_texts_to_tooltips:
            # Turn the help texts into tooltips instead of static text blocks
            for field in self.fields.values():
                field.widget.attrs.update({
                    'aria-label': field.help_text,
                    'data-toggle': 'tooltip',
                    'data-placement': 'bottom',
                    'data-html': 'true',
                    'data-trigger': 'hover',
                    'title': field.help_text,
                })
                field.help_text = None

    def clean(self):
        super().clean()
        points = self.cleaned_data.get("points")
        max_points = self.exercise.max_points
        if points is not None and points > max_points:
            raise forms.ValidationError(
                format_lazy(
                    _('SUBMISSION_REVIEW_ERROR_POINTS_GREATER_THAN_MAX_POINTS -- {max:d}'),
                    max=self.exercise.max_points
                )
            )
        return self.cleaned_data


class SubmissionCreateAndReviewForm(SubmissionReviewForm):
    STUDENT_FIELDS = ('students', 'students_by_user_id', 'students_by_student_id', 'students_by_email')

    submission_time = forms.DateTimeField(
        label=_('LABEL_SUBMISSION_TIME'),
    )
    students = forms.ModelMultipleChoiceField(
        queryset=UserProfile.objects.none(),
        required=False,
        label=_('LABEL_STUDENTS'),
    )
    students_by_user_id = forms.TypedMultipleChoiceField(
        empty_value=UserProfile.objects.none(),
        coerce=lambda user_id: User.objects.get(id=user_id).userprofile,
        choices=[],
        required=False,
        label=_('LABEL_STUDENTS_BY_USER_ID'),
    )
    students_by_student_id = forms.TypedMultipleChoiceField(
        empty_value=UserProfile.objects.none(),
        coerce=lambda student_id: UserProfile.get_by_student_id(student_id), # pylint: disable=unnecessary-lambda
        choices=[],
        required=False,
        label=_('LABEL_STUDENTS_BY_STUDENT_ID'),
    )
    students_by_email = forms.TypedMultipleChoiceField(
        empty_value=UserProfile.objects.none(),
        coerce=lambda email: UserProfile.get_by_email(email), # pylint: disable=unnecessary-lambda
        choices=[],
        required=False,
        label=_('LABEL_STUDENTS_BY_EMAIL'),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["students"].queryset = \
            UserProfile.objects.all()
        self.fields["students_by_user_id"].choices = \
            [ (p.user_id, p) for p in UserProfile.objects.all() ]
        self.fields["students_by_student_id"].choices = \
            [ (p.student_id, p.student_id) for p in UserProfile.objects.all() ]
        self.fields["students_by_email"].choices = \
            [ (u.email, u.email) for u in User.objects.all() ]

    def clean(self):
        self.cleaned_data = data = super().clean()
        fields = self.STUDENT_FIELDS
        n = sum((1 if data.get(k) else 0) for k in fields)
        if n == 0:
            raise forms.ValidationError(_('SUBMISSION_CREATE_AND_REVIEW_ERROR_ALL_STUDENT_FIELDS_BLANK'))
        if n > 1:
            raise forms.ValidationError(_('SUBMISSION_CREATE_AND_REVIEW_ERROR_ONLY_ONE_STUDENT_FIELD_CAN_BE_GIVEN'))
        return data

    @property
    def cleaned_students(self):
        data = self.cleaned_data
        for field in self.STUDENT_FIELDS:
            s = data.get(field)
            if s:
                return s
        raise RuntimeError("Didn't find any students")


class EditSubmittersForm(forms.ModelForm):

    submitters = UsersSearchSelectField(
        queryset=UserProfile.objects.none(),
        initial_queryset=UserProfile.objects.none(),
        label=_('LABEL_SUBMITTERS'),
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        course_instance = kwargs.get('instance').exercise.course_instance
        super().__init__(*args, **kwargs)
        self.fields['submitters'].widget.search_api_url = api_reverse(
            "course-students-list",
            kwargs={'course_id': course_instance.id},
        )
        self.fields['submitters'].queryset = course_instance.get_student_profiles()
        self.fields['submitters'].initial_queryset = self.instance.submitters.all()

    class Meta:
        model = Submission
        fields = ['submitters']
