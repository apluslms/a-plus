from django import forms
from django.utils.translation import gettext_lazy as _

from .models import News


class NewsForm(forms.ModelForm):

    email = forms.BooleanField(
        required=False,
        label=_("SEND_EMAIL_TO_STUDENTS"),
    )

    class Meta:
        model = News
        fields = [
            'audience',
            'publish',
            'pin',
            'email',
            'title',
            'body',
        ]
