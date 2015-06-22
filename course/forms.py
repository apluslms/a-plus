from django import forms
from django.utils.translation import gettext_lazy as _

from exercise.models import CourseModule, LearningObjectCategory, \
    BaseExercise, ExerciseWithAttachment
from userprofile.models import UserProfile


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


class BaseExerciseForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(BaseExerciseForm, self).__init__(*args, **kwargs)
        
        self.exercise = kwargs.get('instance')
        
        self.fields["course_module"].queryset = CourseModule.objects.filter(
            course_instance=self.exercise.course_instance)
        self.fields["category"].queryset = LearningObjectCategory.objects.filter(
            course_instance=self.exercise.course_instance)

    class Meta:
        model = BaseExercise
        fields = [
            'service_url',
            'name',
            'description',
            'category',
            'course_module',
            'order',
            'max_submissions',
            'max_points',
            'points_to_pass',
            'allow_assistant_grading',
            'min_group_size',
            'max_group_size'
        ]

    def get_fieldsets(self):
        return [
            {"legend": _("Exercise"), "fields": self.get_exercise_fields()},
            {"legend": _("Grading"), "fields": self.get_grading_fields()},
            {"legend": _("Groups"), "fields": self.get_group_fields()},
        ]

    def get_exercise_fields(self):
        return (self["name"],
                self["description"],
                self["category"],
                self["course_module"],
                self["order"])

    def get_grading_fields(self):
        return (self["max_submissions"],
                self["max_points"],
                self["points_to_pass"],
                self["allow_assistant_grading"])

    def get_group_fields(self):
        return (self["min_group_size"],
                self["max_group_size"])


class ExerciseWithAttachmentForm(BaseExerciseForm):

    def __init__(self, *args, **kwargs):
        super(ExerciseWithAttachmentForm, self).__init__(*args, **kwargs)

    class Meta:
        model = ExerciseWithAttachment
        fields = [
            'service_url',
            'name',
            'instructions',
            'category',
            'course_module',
            'order',
            'files_to_submit',
            'attachment',
            'max_submissions',
            'max_points',
            'points_to_pass',
            'allow_assistant_grading',
            'min_group_size',
            'max_group_size'
        ]

    def get_exercise_fields(self):
        return (self["name"],
                self["instructions"],
                self["category"],
                self["course_module"],
                self["order"],
                self["files_to_submit"],
                self["attachment"])


class DeadlineRuleDeviationForm(forms.Form):
    
    exercise = forms.ModelMultipleChoiceField(queryset=BaseExercise.objects.none(),
        help_text=_("Hold down 'Control', or 'Command' on a Mac, to select more than one exercise."))
    submitter = forms.ModelMultipleChoiceField(queryset=UserProfile.objects.none(),
        help_text=_("Hold down 'Control', or 'Command' on a Mac, to select more than one student."))
    minutes = forms.IntegerField(
        help_text=_("Amount of extra time given in minutes."))
    
    def __init__(self, *args, **kwargs):
        course_instance = kwargs.pop('instance')
        super(DeadlineRuleDeviationForm, self).__init__(*args, **kwargs)
        
        self.fields["exercise"].queryset = BaseExercise.objects.filter(
            course_module__course_instance=course_instance)
        self.fields["submitter"].queryset = UserProfile.objects.filter(
            submissions__exercise__course_module__course_instance=course_instance).distinct()
