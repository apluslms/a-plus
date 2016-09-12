from django import forms
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from userprofile.models import UserProfile


class SubmissionCallbackForm(forms.Form):
    """
    Parses and validates the grading callback request.
    """
    points = forms.IntegerField(min_value=0)
    max_points = forms.IntegerField(min_value=0, required=False)
    feedback = forms.CharField(required=False)
    notificate = forms.CharField(required=False)
    grading_payload = forms.CharField(required=False)
    error = forms.BooleanField(required=False)

    def clean(self):
        points      = self.cleaned_data.get("points")
        max_points  = self.cleaned_data.get("max_points", 0)
        if points and max_points:
            if points > max_points:
                raise forms.ValidationError(
                    _("Points greater than maximum points are not allowed."))
            if points < 0:
                raise forms.ValidationError(
                    _("Points lower than zero are not allowed."))
        return self.cleaned_data


class SubmissionReviewForm(forms.Form):

    points = forms.IntegerField(min_value=0,
        help_text=_("Possible penalties are not applied - the points are set "
                    "as given. This will <em>override</em> grader points!"))
    assistant_feedback = forms.CharField(required=False, widget=forms.Textarea,
        help_text=_("HTML formatting is allowed. This will not override "
                    "machine feedback."))
    feedback = forms.CharField(required=False, widget=forms.Textarea,
        help_text=_("HTML formatting is allowed. This WILL override machine "
                    "feedback."))

    def __init__(self, *args, **kwargs):
        self.exercise = kwargs.pop('exercise')
        super(SubmissionReviewForm, self).__init__(*args, **kwargs)

    def clean(self):
        super().clean()
        points = self.cleaned_data.get("points")
        max_points = self.exercise.max_points
        if not points is None and points > max_points:
            raise forms.ValidationError(
                _("The maximum points for this exercise is {max:d} and the "
                  "given points is more than that.").format(
                    max=self.exercise.max_points
                ))
        return self.cleaned_data


class SubmissionCreateAndReviewForm(SubmissionReviewForm):

    submission_time = forms.DateTimeField()
    students = forms.ModelMultipleChoiceField(
        queryset=UserProfile.objects.none(), required=False)
    students_by_student_id = forms.TypedMultipleChoiceField(
        empty_value=UserProfile.objects.none(),
        coerce=lambda student_id: UserProfile.get_by_student_id(student_id),
        choices=[(p.student_id, p.student_id) for p in UserProfile.objects.none()],
        required=False)
    students_by_email = forms.TypedMultipleChoiceField(
        empty_value=UserProfile.objects.none(),
        coerce=lambda email: UserProfile.get_by_email(email),
        choices=[(u.email, u.email) for u in User.objects.none()],
        required=False)

    def __init__(self, *args, **kwargs):
        super(SubmissionCreateAndReviewForm, self).__init__(*args, **kwargs)
        self.fields["students"].queryset = \
            UserProfile.objects.all()
            #self.exercise.course_instance.get_student_profiles()
        self.fields["students_by_student_id"].choices = \
            [ (p.student_id, p.student_id) for p in UserProfile.objects.all()
              #self.exercise.course_instance.get_student_profiles()
            ]
        self.fields["students_by_email"].choices = \
            [ (u.email, u.email) for u in User.objects.all() ]

    def clean(self):
        self.cleaned_data = super(SubmissionCreateAndReviewForm, self).clean()
        n = 0
        if self.cleaned_data.get("students"):
            n += 1
        if self.cleaned_data.get("students_by_student_id"):
            n += 1
        if self.cleaned_data.get("students_by_email"):
            n += 1
        if n == 0:
            raise forms.ValidationError(
                _("One of the student fields must not be blank: students, students_by_student_id, students_by_email"))
        if n > 1:
            raise forms.ValidationError(
                _("Only one student field can be given: students, students_by_student_id, students_by_email"))
        return self.cleaned_data
