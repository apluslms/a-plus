from django import forms
from django.utils.translation import ugettext_lazy as _

from exercise.forms import SubmissionCreateAndReviewForm
from userprofile.models import UserProfile


class BatchSubmissionCreateAndReviewForm(SubmissionCreateAndReviewForm):

    grader = forms.ModelChoiceField(queryset=UserProfile.objects.none(),
        required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["grader"].queryset = \
            UserProfile.objects.all()
            #self.exercise.course_instance.get_course_staff_profiles()
