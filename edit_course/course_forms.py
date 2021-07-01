from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django_colortag.forms import ColorTagForm

from aplus.api import api_reverse
from course.models import LearningObjectCategory, Course, CourseModule, CourseInstance, UserTag
from lib.validators import generate_url_key_validator
from lib.fields import UsersSearchSelectField
from userprofile.models import UserProfile


class FieldsetModelForm(forms.ModelForm):

    class Meta:
        legend = ""
        fields = []

    def get_fieldsets(self):
        return [
            { "legend": self.Meta.legend, "fields": self.get_fields(*self.Meta.fields) },
        ]

    def get_fields(self, *names):
        return [self[name] for name in names]


class LearningObjectCategoryForm(FieldsetModelForm):

    class Meta:
        model = LearningObjectCategory
        legend = _('CATEGORY_capitalized')
        fields = [
            'status',
            'name',
            'points_to_pass',
            'confirm_the_level',
            'accept_unofficial_submits',
            'description'
        ]


class CourseModuleForm(FieldsetModelForm):

    class Meta:
        model = CourseModule
        fields = [
            'status',
            'order',
            'name',
            'url',
            'introduction',
            'points_to_pass',
            'opening_time',
            'reading_opening_time',
            'closing_time',
            'late_submissions_allowed',
            'late_submission_deadline',
            'late_submission_penalty'
        ]

    def get_fieldsets(self):
        return [
            { 'legend':_('HIERARCHY'), 'fields':self.get_fields('status','order','url') },
            { 'legend':_('CONTENT'), 'fields':self.get_fields('name','introduction','points_to_pass') },
            { 'legend':_('SCHEDULE'), 'fields':self.get_fields('reading_opening_time','opening_time','closing_time',
                'late_submissions_allowed','late_submission_deadline', 'late_submission_penalty') },
        ]


class CourseInstanceForm(forms.ModelForm):

    assistants = UsersSearchSelectField(queryset=UserProfile.objects.all(),
        initial_queryset=UserProfile.objects.none(),
        required=False) # Not required because a course does not have to have any assistants.

    class Meta:
        model = CourseInstance
        fields = [
            'visible_to_students',
            'instance_name',
            'url',
            'image',
            'language',
            'starting_time',
            'ending_time',
            'lifesupport_time',
            'archive_time',
            'enrollment_starting_time',
            'enrollment_ending_time',
            'enrollment_audience',
            'view_content_to',
            'head_urls',
            'assistants',
            'technical_error_emails',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assistants'].initial_queryset = self.instance.assistants.all()
        self.fields['assistants'].widget.attrs["data-search-api-url"] = api_reverse("user-list")
        if self.instance and self.instance.visible_to_students:
            self.fields["url"].widget.attrs["readonly"] = "true"
            self.fields["url"].help_text = _('COURSE_URL_IDENTIFIER_LOCKED_WHILE_COURSE_VISIBLE')
            self.fields["lifesupport_time"].help_text = _('COURSE_REMOVES_MODEL_ANSWER_VISIBILITY_STUDENTS')
            self.fields["archive_time"].help_text = _('COURSE_REMOVES_SUBMISSION_POSSIBILITY_STUDENTS')

    def clean_url(self):
        if self.instance and self.instance.visible_to_students:
            # URL must not be changed for visible course instances.
            return self.instance.url
        # ModelForm runs form validation before the model validation.
        # The URL validator is copied here from the model definition because
        # the cleaned data returned here is used in the rendering of the form
        # POST target page. Even though the model validation would stop invalid
        # data from being saved to the database, the next page rendering could
        # crash due to invalid data if this method returned an invalid value.
        # Raising a ValidationError here prevents the course instance from
        # having invalid values.
        generate_url_key_validator()(self.cleaned_data["url"])
        return self.cleaned_data["url"]


class CourseIndexForm(forms.ModelForm):

    class Meta:
        model = CourseInstance
        fields = [
            'index_mode',
            'description',
            'footer',
        ]


class CourseContentForm(forms.ModelForm):

    class Meta:
        model = CourseInstance
        fields = [
            'module_numbering',
            'content_numbering',
        ]


class CourseTeachersForm(forms.ModelForm):

    teachers = UsersSearchSelectField(queryset=UserProfile.objects.all(),
        initial_queryset=UserProfile.objects.none(),
        required=False) # Not required because a course does not have to have any teachers.

    class Meta:
        model = Course
        fields = [
            'teachers'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['teachers'].initial_queryset = self.instance.teachers.all()
        self.fields['teachers'].widget.attrs["data-search-api-url"] = api_reverse("user-list")


class CloneInstanceForm(forms.Form):
    url = forms.CharField(label=_('COURSE_NEW_URL_IDENTIFIER_COURSE_INSTANCE'),
        validators=[generate_url_key_validator()])
    assistants = forms.BooleanField(label=_('ASSISTANTS'), required=False, initial=True)
    categories = forms.BooleanField(label=_('EXERCISE_CATEGORIES'), required=False, initial=True)
    modules = forms.BooleanField(label=_('COURSE_MODULES'), required=False, initial=True)
    chapters = forms.BooleanField(label=_('CONTENT_CHAPTERS'), required=False, initial=True)
    exercises = forms.BooleanField(label=_('EXERCISES'), required=False, initial=True)
    menuitems = forms.BooleanField(label=_('MENU_ITEMS'), required=False, initial=True)
    usertags = forms.BooleanField(label=_('STUDENT_TAGS'), required=False, initial=True)

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance')
        super().__init__(*args, **kwargs)

    def clean_url(self):
        url = self.cleaned_data['url']
        if CourseInstance.objects.filter(
                course=self.instance.course, url=url).exists():
            raise ValidationError(_('ERROR_URL_ALREADY_TAKEN'))
        return url

    def clean(self):
        errors = {}
        if self.cleaned_data['chapters'] or self.cleaned_data['exercises']:
            if not self.cleaned_data['categories']:
                errors['categories'] = _(
                    'ERROR_CATEGORIES_NEED_CLONING_TO_CLONE_CHAPTERS_AND_EXERCISES'
                )
            if not self.cleaned_data['modules']:
                errors['modules'] = _(
                    'ERROR_MODULES_NEED_CLONING_TO_CLONE_CHAPTERS_AND_EXERCISES'
                )

        if errors:
            raise ValidationError(errors)


class UserTagForm(ColorTagForm):

    class Meta(ColorTagForm.Meta):
        model = UserTag
        fields = [
            'name',
            'slug',
            'description',
            'visible_to_students',
            'color',
        ]

    @classmethod
    def get_base_object(self, course_instance):
        obj = self.Meta.model()
        obj.course_instance = course_instance
        return obj

class SelectUsersForm(forms.Form):
    user = UsersSearchSelectField(queryset=UserProfile.objects.none(),
        initial_queryset=UserProfile.objects.none())

    def __init__(self, *args, **kwargs):
        course_instance = kwargs.pop('instance')
        super(SelectUsersForm, self).__init__(*args, **kwargs)
        self.fields['user'].widget.attrs["data-search-api-url"] = api_reverse(
            "course-students-list", kwargs={'course_id': course_instance.id})
        self.fields['user'].queryset = course_instance.get_student_profiles()
