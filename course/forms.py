from django import forms
from exercise.exercise_models import CourseModule

class CourseModuleForm(forms.ModelForm):
    class Meta:
        model = CourseModule
        fields = ['name', 'points_to_pass', 'introduction',
                  'opening_time', 'closing_time',
                  'late_submissions_allowed', 'late_submission_deadline', 'late_submission_penalty']
