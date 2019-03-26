from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django_colortag.forms import ColorTagForm

from course.models import LearningObjectCategory, CourseModule, CourseInstance, UserTag
from lib.validators import generate_url_key_validator
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
        legend = _("Category")
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
            'closing_time',
            'late_submissions_allowed',
            'late_submission_deadline',
            'late_submission_penalty'
        ]

    def get_fieldsets(self):
        return [
            { 'legend':_('Hierarchy'), 'fields':self.get_fields('status','order','url') },
            { 'legend':_('Content'), 'fields':self.get_fields('name','introduction','points_to_pass') },
            { 'legend':_('Schedule'), 'fields':self.get_fields('opening_time','closing_time',
                'late_submissions_allowed','late_submission_deadline', 'late_submission_penalty') },
        ]


class CourseInstanceForm(forms.ModelForm):

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
        self.fields["assistants"].widget.attrs["class"] = "search-select"
        self.fields["assistants"].help_text = ""
        if self.instance and self.instance.visible_to_students:
            self.fields["url"].widget.attrs["readonly"] = "true"
            self.fields["url"].help_text = _("The URL identifier is locked "
                "while the course is visible to students.")
            self.fields["lifesupport_time"].help_text = _("Removes visibility "
                "of model answers for students.")
            self.fields["archive_time"].help_text = _("Removes possibility "
                "for students to return answers.")

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


class CloneInstanceForm(forms.Form):
    url = forms.CharField(label=_("New URL identifier for the course instance:"),
        validators=[generate_url_key_validator()])

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance')
        super().__init__(*args, **kwargs)

    def clean_url(self):
        url = self.cleaned_data['url']
        if CourseInstance.objects.filter(
                course=self.instance.course, url=url).exists():
            raise ValidationError(_("The URL is already taken."))
        return url

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
    user = forms.ModelMultipleChoiceField(queryset=UserProfile.objects.none())

    def __init__(self, *args, **kwargs):
        # This is copied from deviations/forms.py, which itself is not DRY.
        # TODO: refactor this and the aforementioned form to avoid repetition
        course_instance = kwargs.pop('instance')
        super(SelectUsersForm, self).__init__(*args, **kwargs)
        self.fields['user'].widget.attrs['class'] = 'search-select'
        self.fields['user'].help_text = ''
        self.fields['user'].queryset = course_instance.get_student_profiles()
