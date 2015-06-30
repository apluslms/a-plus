import logging

from django import forms
from django.utils.translation import ugettext_lazy as _

from course.models import CourseModule, LearningObjectCategory
from exercise.models import BaseExercise, ExerciseWithAttachment


logger = logging.getLogger("aplus.exercise")

def get_form(course_module, exercise_type, exercise=None, request=None):
    if not exercise:
        if exercise_type == "exercise_with_attachment":
            exercise = ExerciseWithAttachment(course_module=course_module)
        elif exercise_type == None:
            exercise = BaseExercise(course_module=course_module)
        else:
            raise TypeError("Unknown exercise type key")
    if isinstance(exercise, ExerciseWithAttachment):
        form_cls = ExerciseWithAttachmentForm
    elif isinstance(exercise, BaseExercise):
        form_cls = BaseExerciseForm
    else:
        logger.error("Tried to edit unexpected exercise type: %s", type(exercise))
        raise TypeError("Unknown exercise type instance")
    
    if request:
        return form_cls(request.POST, request.FILES, instance=exercise)
    return form_cls(instance=exercise)


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
