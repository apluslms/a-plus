from datetime import datetime

from django.forms import ModelForm, SplitDateTimeField, HiddenInput

from .models import ExamSession
from course.models import CourseModule


class ExamSessionForm(ModelForm):

    class Meta:
        model = ExamSession
        fields = ['course_instance', 'exam_module', 'room']

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop('course_instance')
        super().__init__(*args, **kwargs)

        self.fields['course_instance'].initial = instance
        self.fields['course_instance'].widget = HiddenInput()
        self.fields['exam_module'].queryset = CourseModule.objects.filter(
            course_instance=instance)
