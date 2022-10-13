from django import forms

from exercise.forms import SubmissionCreateAndReviewForm
from userprofile.models import UserProfile


class BatchSubmissionCreateAndReviewForm(SubmissionCreateAndReviewForm):

    grader = forms.ModelChoiceField(queryset=UserProfile.objects.none(),
        required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["grader"].queryset = \
            UserProfile.objects.all()
