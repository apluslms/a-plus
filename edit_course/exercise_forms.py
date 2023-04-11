import logging
from typing import Any, Dict, List

from django import forms
from django.utils.translation import gettext_lazy as _

from course.models import CourseModule, LearningObjectCategory
from exercise.models import LearningObject, CourseChapter, BaseExercise, \
    LTIExercise, StaticExercise, ExerciseWithAttachment, RevealRule
from lib.widgets import DateTimeLocalInput
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
    'grading_mode',
]


class LearningObjectMixin:

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


class RevealRuleForm(FieldsetModelForm):
    # This form is only used internally by BaseExerciseForm.

    class Meta:
        model = RevealRule
        fields = ['trigger', 'delay_minutes', 'time', 'currently_revealed']
        widgets = {'time': DateTimeLocalInput}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields['trigger'].widget.attrs['data-trigger'] = True
        # Visibility rules for the form fields. Each of the following fields is
        # only visible when one of their specified values is selected from the
        # trigger dropdown. See edit_model.html.
        self.fields['currently_revealed'].widget.attrs['data-visible-triggers'] = [
            RevealRule.TRIGGER.MANUAL.value,
        ]
        self.fields['time'].widget.attrs['data-visible-triggers'] = [
            RevealRule.TRIGGER.TIME.value,
        ]
        self.fields['delay_minutes'].widget.attrs['data-visible-triggers'] = [
            RevealRule.TRIGGER.DEADLINE.value,
            RevealRule.TRIGGER.DEADLINE_ALL.value,
        ]

    def clean(self) -> Dict[str, Any]:
        result = super().clean()
        errors = {}
        trigger = self.cleaned_data.get('trigger')
        if trigger == RevealRule.TRIGGER.TIME:
            time = self.cleaned_data.get('time')
            if time is None:
                errors['time'] = _(
                    'ERROR_REQUIRED_WITH_SELECTED_TRIGGER'
                )
        if errors:
            raise forms.ValidationError(errors)
        return result


class BaseExerciseForm(LearningObjectMixin, FieldsetModelForm):

    class Meta:
        model = BaseExercise
        fields = COMMON_FIELDS + SERVICE_FIELDS + EXERCISE_FIELDS

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.init_fields(**kwargs)

        # This form contains two embedded RevealRuleForms.
        self.submission_feedback_form = RevealRuleForm(
            data=kwargs.get('data'),
            instance=self.instance.active_submission_feedback_reveal_rule,
            prefix='submission_feedback',
        )
        self.model_solutions_form = RevealRuleForm(
            data=kwargs.get('data'),
            instance=self.instance.active_model_solutions_reveal_rule,
            prefix='model_solutions',
        )

    def get_fieldsets(self) -> List[Dict[str, Any]]:
        return [
            self.get_hierarchy_fieldset(),
            self.get_content_fieldset('model_answers', 'templates'),
            { 'legend':_('GRADING'), 'fields':self.get_fields('max_submissions',
                'max_points','points_to_pass', 'difficulty',
                'allow_assistant_viewing','allow_assistant_grading','grading_mode') },
            { 'legend':_('GROUPS'), 'fields':self.get_fields('min_group_size',
                'max_group_size') },
            { 'legend':_('REVEAL_SUBMISSION_FEEDBACK'), 'fields':self.submission_feedback_form },
            { 'legend':_('REVEAL_MODEL_SOLUTIONS'), 'fields':self.model_solutions_form },
        ]

    def is_valid(self) -> bool:
        return (
            super().is_valid()
            and self.submission_feedback_form.is_valid()
            and self.model_solutions_form.is_valid()
        )

    def save(self, *args: Any, **kwargs: Any) -> Any:
        # Save the reveal rules only if they have been changed.
        # If they were not changed, we can keep using the default rule and
        # there's no need to save a new RevealRule.
        if self.submission_feedback_form.has_changed():
            self.instance.submission_feedback_reveal_rule = (
                self.submission_feedback_form.save(*args, **kwargs)
            )
        if self.model_solutions_form.has_changed():
            self.instance.model_solutions_reveal_rule = (
                self.model_solutions_form.save(*args, **kwargs)
            )
        return super().save(*args, **kwargs)


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
