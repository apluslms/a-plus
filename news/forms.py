from django import forms
from django.utils.translation import gettext_lazy as _

from .models import News


class NewsForm(forms.ModelForm):

    email_students = forms.BooleanField(
        required=False,
        label=_("SEND_EMAIL_TO_STUDENTS"),
    )
    email_staff = forms.BooleanField(
        required=False,
        label=_("SEND_EMAIL_TO_STAFF"),
    )

    class Meta:
        model = News
        fields = [
            'audience',
            'publish',
            'pin',
            'email_students',
            'email_staff',
            'language',
            'title',
            'body',
        ]
