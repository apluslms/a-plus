from django import forms
from django.utils.translation import ugettext_lazy as _

from exercise.models import BaseExercise
from userprofile.models import UserProfile


class DeadlineRuleDeviationForm(forms.Form):

    exercise = forms.ModelMultipleChoiceField(
        queryset=BaseExercise.objects.none(),
    )
    submitter = forms.ModelMultipleChoiceField(
        queryset=UserProfile.objects.none(),
    )
    minutes = forms.IntegerField(
        min_value=1,
        help_text=_("Amount of extra time given in minutes."),
    )
    without_late_penalty = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Do not apply late penalty during extra time."),
    )

    def __init__(self, *args, **kwargs):
        course_instance = kwargs.pop('instance')
        super(DeadlineRuleDeviationForm, self).__init__(*args, **kwargs)
        self.fields["exercise"].widget.attrs["class"] = "search-select"
        self.fields["exercise"].help_text = ""
        self.fields["exercise"].queryset = BaseExercise.objects.filter(
            course_module__course_instance=course_instance
        )
        self.fields["submitter"].widget.attrs["class"] = "search-select"
        self.fields["submitter"].help_text = ""
        self.fields["submitter"].queryset = UserProfile.objects.filter(
            submissions__exercise__course_module__course_instance=course_instance
        ).distinct()
