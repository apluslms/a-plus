from django import forms

from .models import CourseRepo


class CourseRepoForm(forms.ModelForm):

    class Meta:
        model = CourseRepo
        fields = [
            'key',
            'git_origin',
            'git_branch',
            'update_hook',
        ]
