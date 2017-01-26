from django import forms

from .models import News


class NewsForm(forms.ModelForm):

    class Meta:
        model = News
        fields = [
            'audience',
            'publish',
            'pin',
            'alert',
            'title',
            'body',
        ]
