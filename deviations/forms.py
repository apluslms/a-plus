from typing import Any, Dict, Optional

from django import forms
from django.utils.translation import gettext_lazy as _

from aplus.api import api_reverse
from exercise.models import BaseExercise
from userprofile.models import UserProfile
from course.models import CourseModule, UserTag
from lib.fields import DurationField, UsersSearchSelectField, SearchSelect
from lib.widgets import DateTimeLocalInput


class BaseDeviationForm(forms.Form):
    """
    Base class for deviation forms.
    """
    module = forms.ModelMultipleChoiceField(
        queryset=CourseModule.objects.none(),
        required=False,
        label=_('LABEL_MODULE'),
        widget=SearchSelect,
    )
    exercise = forms.ModelMultipleChoiceField(
        queryset=BaseExercise.objects.none(),
        required=False,
        label=_('LABEL_EXERCISE'),
        widget=SearchSelect,
    )
    submitter_tag = forms.ModelMultipleChoiceField(
        queryset=UserTag.objects.none(),
        required=False,
        label=_('LABEL_SUBMITTER_TAG'),
        widget=SearchSelect(display_fields=['slug']),
    )
    submitter = UsersSearchSelectField(
        queryset=UserProfile.objects.none(),
        initial_queryset=UserProfile.objects.none(),
        required=False,
        label=_('LABEL_SUBMITTER'),
    )

    def __init__(self, *args: Any, initial: Optional[Dict[str, Any]] = None, **kwargs: Any) -> None:
        course_instance = kwargs.pop('instance')
        super().__init__(*args, initial=initial, **kwargs)
        self.fields['module'].queryset = CourseModule.objects.filter(
            course_instance=course_instance
        )
        self.fields['exercise'].queryset = BaseExercise.objects.filter(
            course_module__course_instance=course_instance
        )
        self.fields['submitter_tag'].queryset = course_instance.usertags
        self.fields['submitter'].queryset = course_instance.get_student_profiles()
        if initial is not None:
            try:
                # Support setting the initial value for submitter
                self.fields['submitter'].initial_queryset = (
                    course_instance.get_student_profiles().filter(id__in=initial.get('submitter'))
                )
            except (ValueError, TypeError):
                pass
        self.fields['submitter'].widget.search_api_url = api_reverse(
            "course-students-list",
            kwargs={'course_id': course_instance.id},
        )

    def clean(self) -> Dict[str, Any]:
        cleaned_data = super().clean()
        module = cleaned_data.get("module")
        exercise = cleaned_data.get("exercise")
        if not exercise and not module:
            raise forms.ValidationError(
                _("EXERCISES_AND_MODULES_MISSING"))
        submitter_tag = cleaned_data.get("submitter_tag")
        submitter = cleaned_data.get("submitter")
        if not submitter_tag and not submitter:
            raise forms.ValidationError(
                _("SUBMITTERS_AND_TAGS_MISSING"))
        return cleaned_data


class DeadlineRuleDeviationForm(BaseDeviationForm):
    minutes = DurationField(
        required=False,
        min_value=1,
        label=_('LABEL_MINUTES'),
        help_text=_('DEVIATION_EXTRA_MINUTES_HELPTEXT'),
    )
    new_date = forms.DateTimeField(
        required=False,
        label=_('LABEL_NEW_DEADLINE'),
        help_text=_('DEVIATION_NEW_DEADLINE_DATE_HELPTEXT'),
        widget=DateTimeLocalInput,
    )
    without_late_penalty = forms.BooleanField(
        required=False,
        initial=True,
        label=_('LABEL_WITHOUT_LATE_PENALTY'),
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields['module'].help_text = _('DEVIATION_MODULE_ADD_HELPTEXT')
        self.fields['exercise'].help_text = _('DEVIATION_EXERCISE_ADD_HELPTEXT')
        self.fields['submitter_tag'].help_text = _('DEVIATION_SUBMITTER_TAG_ADD_HELPTEXT')
        self.fields['submitter'].help_text = _('DEVIATION_SUBMITTER_ADD_HELPTEXT')

    def clean(self) -> Dict[str, Any]:
        cleaned_data = super().clean()
        new_date = cleaned_data.get("new_date")
        minutes = cleaned_data.get("minutes")
        if minutes and new_date or not minutes and not new_date:
            raise forms.ValidationError(
                _("MINUTES_AND_DATE_MISSING"))
        return cleaned_data


class MaxSubmissionRuleDeviationForm(BaseDeviationForm):
    extra_submissions = forms.IntegerField(
        required=True,
        min_value=1,
        label=_('LABEL_EXTRA_SUBMISSIONS'),
    )

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields['module'].help_text = _('DEVIATION_MODULE_ADD_HELPTEXT')
        self.fields['exercise'].help_text = _('DEVIATION_EXERCISE_ADD_HELPTEXT')
        self.fields['submitter_tag'].help_text = _('DEVIATION_SUBMITTER_TAG_ADD_HELPTEXT')
        self.fields['submitter'].help_text = _('DEVIATION_SUBMITTER_ADD_HELPTEXT')


class RemoveDeviationForm(BaseDeviationForm):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.fields['module'].help_text = _('DEVIATION_MODULE_REMOVE_HELPTEXT')
        self.fields['exercise'].help_text = _('DEVIATION_EXERCISE_REMOVE_HELPTEXT')
        self.fields['submitter_tag'].help_text = _('DEVIATION_SUBMITTER_TAG_REMOVE_HELPTEXT')
        self.fields['submitter'].help_text = _('DEVIATION_SUBMITTER_REMOVE_HELPTEXT')
