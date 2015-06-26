from django import forms
from course.models import CourseModule


class CourseModuleForm(forms.ModelForm):
    
    class Meta:
        model = CourseModule
        fields = [
            'name',
            'url',
            'points_to_pass',
            'introduction',
            'opening_time',
            'closing_time',
            'late_submissions_allowed',
            'late_submission_deadline',
            'late_submission_penalty'
        ]
