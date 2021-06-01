import logging

from django import forms
from django.utils.translation import gettext_lazy as _

from course.models import CourseModule, LearningObjectCategory
from exercise.models import LearningObject, CourseChapter, BaseExercise, \
    LTIExercise, StaticExercise, ExerciseWithAttachment
from .course_forms import FieldsetModelForm

from exercise.exercisecollection_models import ExerciseCollection

logger = logging.getLogger("aplus.exercise")

COMMON_FIELDS = [
    'status',
    'audience',
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
EXERCISE_FIELDS = [
    'max_submissions',
    'max_points',
    'difficulty',
    'points_to_pass',
    'allow_assistant_viewing',
    'allow_assistant_grading',
    'min_group_size',
    'max_group_size',
    'model_answers',
    'templates',
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

    @property
    def remote_service_head(self):
        return True

    def get_hierarchy_fieldset(self):
        return { 'legend':_('HIERARCHY'), 'fields':self.get_fields('status',
            'audience', 'category','course_module','parent','order','url') }

    def get_content_fieldset(self, *add):
        return { 'legend':_('CONTENT'), 'fields':self.get_fields('name',
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
            self.get_content_fieldset(
                'use_wide_column', 'generate_table_of_contents'),
        ]


class BaseExerciseForm(LearningObjectMixin, FieldsetModelForm):

    class Meta:
        model = BaseExercise
        fields = COMMON_FIELDS + SERVICE_FIELDS + EXERCISE_FIELDS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.init_fields(**kwargs)

    def get_fieldsets(self):
        return [
            self.get_hierarchy_fieldset(),
            self.get_content_fieldset('model_answers', 'templates'),
            { 'legend':_('GRADING'), 'fields':self.get_fields('max_submissions',
                'max_points','points_to_pass', 'difficulty',
                'allow_assistant_viewing','allow_assistant_grading') },
            { 'legend':_('GROUPS'), 'fields':self.get_fields('min_group_size',
                'max_group_size') },
        ]


class LTIExerciseForm(BaseExerciseForm):

    class Meta:
        model = LTIExercise
        fields = COMMON_FIELDS + SERVICE_FIELDS + EXERCISE_FIELDS + [
            'lti_service',
            'context_id',
            'resource_link_id',
            'resource_link_title',
            'aplus_get_and_post',
            'open_in_iframe',
        ]

    @property
    def remote_service_head(self):
        return False

    def get_content_fieldset(self, *add):
        return super().get_content_fieldset('lti_service','context_id',
            'resource_link_id','resource_link_title',
            'aplus_get_and_post','open_in_iframe','service_url')


class ExerciseWithAttachmentForm(BaseExerciseForm):
    multipart = True

    class Meta:
        model = ExerciseWithAttachment
        fields = COMMON_FIELDS + SERVICE_FIELDS + EXERCISE_FIELDS + [
            'content',
            'files_to_submit',
            'attachment',
        ]

    def get_content_fieldset(self, *add):
        return super().get_content_fieldset(
            'content', 'files_to_submit', 'attachment')


class StaticExerciseForm(BaseExerciseForm):

    class Meta:
        model = StaticExercise
        fields = COMMON_FIELDS + EXERCISE_FIELDS + [
            'name',
            'description',
            'exercise_page_content',
            'submission_page_content',
        ]

    @property
    def remote_service_head(self):
        return False

    def get_content_fieldset(self, *add):
        return super().get_content_fieldset(
            'exercise_page_content', 'submission_page_content')

class ExerciseCollectionExerciseForm(BaseExerciseForm):

    class Meta:
        model = ExerciseCollection
        fields = COMMON_FIELDS + EXERCISE_FIELDS + SERVICE_FIELDS + \
                 ['target_category']

    def get_content_fieldset(self, *add):
        return super().get_content_fieldset('target_category')
