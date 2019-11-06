from datetime import datetime

from django.forms import ModelForm, SplitDateTimeField, ModelChoiceField

from .models import ExamSession
from course.models import CourseModule, CourseInstance


class ExamSessionForm(ModelForm):

    can_start = SplitDateTimeField(initial=datetime.now())

    class Meta:
        model = ExamSession
        fields = ['course_instance', 'exam_module',
                  'can_start', 'duration', 'room']

    def __init__(self, *args, **kwargs):
        instance = kwargs.pop('course_instance')
        super().__init__(*args, **kwargs)

        self.fields['course_instance'].queryset = CourseInstance.objects.filter(
            id=instance.id)
        self.fields['exam_module'].queryset = CourseModule.objects.filter(
            course_instance=instance)
