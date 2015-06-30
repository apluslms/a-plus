from django import forms
from django.utils.translation import ugettext_lazy as _

from exercise.models import BaseExercise
from userprofile.models import UserProfile


class DeadlineRuleDeviationForm(forms.Form):
    
    exercise = forms.ModelMultipleChoiceField(
        queryset=BaseExercise.objects.none(),
        help_text=_("Hold down 'Control', or 'Command' on a Mac, to select more than one exercise.")
    )
    submitter = forms.ModelMultipleChoiceField(
        queryset=UserProfile.objects.none(),
        help_text=_("Hold down 'Control', or 'Command' on a Mac, to select more than one student.")
    )
    minutes = forms.IntegerField(
        help_text=_("Amount of extra time given in minutes.")
    )
    
    def __init__(self, *args, **kwargs):
        course_instance = kwargs.pop('instance')
        super(DeadlineRuleDeviationForm, self).__init__(*args, **kwargs)
        
        self.fields["exercise"].queryset = BaseExercise.objects.filter(
            course_module__course_instance=course_instance
        )
        self.fields["submitter"].queryset = UserProfile.objects.filter(
            submissions__exercise__course_module__course_instance=course_instance
        ).distinct()
