import logging

from django import forms
from django.utils.translation import ugettext_lazy as _

from course.models import CourseModule, LearningObjectCategory
from exercise.models import LearningObject, CourseChapter, BaseExercise, \
    StaticExercise, ExerciseWithAttachment
from .course_forms import FieldsetModelForm


logger = logging.getLogger("aplus.exercise")

COMMON_FIELDS = [
    'status',
    'category',
    'course_module',
    'parent',
    'order',
    'url',
]
SERVICE_FIELDS = [
    'service_url',
    'name',
    'description',
]


class LearningObjectMixin(object):

    def init_fields(self, **kwargs):
        self.lobject = kwargs.get('instance')
        self.fields["category"].queryset = LearningObjectCategory.objects.filter(
            course_instance=self.lobject.course_instance)
        self.fields["course_module"].queryset = CourseModule.objects.filter(
            course_instance=self.lobject.course_instance)
        self.fields["parent"].queryset = LearningObject.objects\
            .exclude(id=self.lobject.id)\
            .filter(course_module=self.lobject.course_module)

    def get_hierarchy_fieldset(self):
        return { 'legend':_('Hierarchy'), 'fields':self.get_fields('status',
            'category','course_module','parent','order','url') }

    def get_content_fieldset(self, *add):
        return { 'legend':_('Content'), 'fields':self.get_fields('name',
            'description', *add) }


class CourseChapterForm(LearningObjectMixin, FieldsetModelForm):

    class Meta:
        model = CourseChapter
        fields = COMMON_FIELDS + SERVICE_FIELDS + [
            'use_wide_column',
            'generate_table_of_contents'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_fields(**kwargs)

    def get_fieldsets(self):
        return [
            self.get_hierarchy_fieldset(),
            self.get_content_fieldset('use_wide_column',
                'generate_table_of_contents'),
        ]



class BaseExerciseForm(LearningObjectMixin, FieldsetModelForm):

    class Meta:
        model = BaseExercise
        fields = COMMON_FIELDS + SERVICE_FIELDS + [
            'max_submissions',
            'max_points',
            'points_to_pass',
            'allow_assistant_grading',
            'min_group_size',
            'max_group_size'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_fields(**kwargs)

    def get_fieldsets(self):
        return [
            self.get_hierarchy_fieldset(),
            self.get_content_fieldset(),
            { 'legend':_('Grading'), 'fields':self.get_fields('max_submissions',
                'max_points','points_to_pass','allow_assistant_grading') },
            { 'legend':_('Groups'), 'fields':self.get_fields('min_group_size',
                'max_group_size') },
        ]


class ExerciseWithAttachmentForm(BaseExerciseForm):
    multipart = True

    class Meta:
        model = ExerciseWithAttachment
        fields = COMMON_FIELDS + SERVICE_FIELDS + [
            'content',
            'files_to_submit',
            'attachment',
        ]

    def get_content_fieldset(self):
        return super().get_content_fieldset(
            'content', 'files_to_submit', 'attachment')


class StaticExerciseForm(BaseExerciseForm):

    class Meta:
        model = StaticExercise
        fields = COMMON_FIELDS + [
            'name',
            'description',
            'exercise_page_content',
            'submission_page_content',
        ]

    def get_content_fieldset(self):
        return super().get_content_fieldset(
            'exercise_page_content', 'submission_page_content')
