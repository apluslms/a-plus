from django.forms import ModelForm

from .models import ExamSession

class ExamSessionForm(ModelForm):
    class Meta:
        model = ExamSession
        fields = ['course_instance', 'exam_module', 'can_start', 'start_time_actual', 'may_leave_time', 'duration', 'room']
