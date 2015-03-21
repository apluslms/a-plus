from django import forms
from exercise.exercise_models import CourseModule

class CourseModuleForm(forms.ModelForm):
    class Meta:
        model = CourseModule
