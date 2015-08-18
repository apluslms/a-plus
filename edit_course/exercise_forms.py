import logging

from django import forms
from django.utils.translation import ugettext_lazy as _

from course.models import CourseModule, LearningObjectCategory
from exercise.models import BaseExercise, StaticExercise, \
    ExerciseWithAttachment


logger = logging.getLogger("aplus.exercise")


class BaseExerciseForm(forms.ModelForm):

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.exercise = kwargs.get("instance")

        self.fields["course_module"].queryset = CourseModule.objects.filter(
            course_instance=self.exercise.course_instance)
        self.fields["category"].queryset = LearningObjectCategory.objects.filter(
            course_instance=self.exercise.course_instance)

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
    multipart = True

    class Meta:
        model = ExerciseWithAttachment
        fields = [
            'service_url',
            'name',
            'description',
            'category',
            'course_module',
            'order',
            'instructions',
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
                self["description"],
                self["category"],
                self["course_module"],
                self["order"],
                self["instructions"],
                self["files_to_submit"],
                self["attachment"])


class StaticExerciseForm(BaseExerciseForm):

    class Meta:
        model = StaticExercise
        fields = [
            'name',
            'description',
            'category',
            'course_module',
            'order',
            'exercise_page_content',
            'submission_page_content',
            'max_submissions',
            'max_points',
            'points_to_pass',
            'allow_assistant_grading',
            'min_group_size',
            'max_group_size'
        ]

    def get_exercise_fields(self):
        return (self["name"],
                self["description"],
                self["category"],
                self["course_module"],
                self["order"],
                self["exercise_page_content"],
                self["submission_page_content"])
