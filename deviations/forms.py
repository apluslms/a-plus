from typing import Any

from django import forms
from django.utils.translation import gettext_lazy as _

from aplus.api import api_reverse
from exercise.models import BaseExercise
from userprofile.models import UserProfile
from course.models import CourseModule
from lib.fields import UsersSearchSelectField, SearchSelect
from lib.widgets import DateTimeLocalInput


class DeadlineRuleDeviationForm(forms.Form):
    module = forms.ModelMultipleChoiceField(
        queryset=CourseModule.objects.none(),
        required=False,
        label=_('LABEL_MODULE'),
        help_text=_('DEVIATION_MODULE_HELPTEXT'),
        widget=SearchSelect,
    )
    exercise = forms.ModelMultipleChoiceField(
        queryset=BaseExercise.objects.none(),
        required=False,
        label=_('LABEL_EXERCISE'),
        help_text=_('DEVIATION_EXERCISE_HELPTEXT'),
        widget=SearchSelect,
    )
    submitter = UsersSearchSelectField(
        queryset=UserProfile.objects.none(),
        initial_queryset=UserProfile.objects.none(),
        required=True,
        label=_('LABEL_SUBMITTER'),
    )
    minutes = forms.IntegerField(
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
        course_instance = kwargs.pop('instance')
        super(DeadlineRuleDeviationForm, self).__init__(*args, **kwargs)
        self.fields["module"].queryset = CourseModule.objects.filter(
            course_instance=course_instance
        )
        self.fields["exercise"].queryset = BaseExercise.objects.filter(
            course_module__course_instance=course_instance
        )
        self.fields['submitter'].queryset = course_instance.get_student_profiles()
        self.fields['submitter'].widget.search_api_url = api_reverse(
            "course-students-list",
            kwargs={'course_id': course_instance.id},
        )
