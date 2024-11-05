import logging
from typing import Any
import urllib.parse

from aplus_auth.payload import Permission, Permissions
from aplus_auth.requests import get as aplus_get
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_colortag.forms import ColorTagForm

from aplus.api import api_reverse
from course.models import LearningObjectCategory, CourseModule, CourseInstance, UserTag, SubmissionTag
from course.sis import get_sis_configuration, StudentInfoSystem
from exercise.models import CourseChapter
from lib.validators import generate_url_key_validator
from lib.fields import UsersSearchSelectField
from lib.widgets import DateTimeLocalInput
from notification.cache import CachedNotifications
from userprofile.models import UserProfile


logger = logging.getLogger("aplus.course")

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
            'late_submission_penalty',
            'model_answer',
        ]
        widgets = {
            'opening_time': DateTimeLocalInput,
            'reading_opening_time': DateTimeLocalInput,
            'closing_time': DateTimeLocalInput,
            'late_submission_deadline': DateTimeLocalInput,
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        from .exercise_forms import RevealRuleForm # pylint: disable=import-outside-toplevel
        self.model_solution_form = RevealRuleForm(
            data=kwargs.get('data'),
            instance=self.instance.active_model_solution_reveal_rule,
            prefix='model_solution',
        )
        self.fields['model_answer'].queryset = CourseChapter.objects.filter(
            course_module__course_instance=self.instance.course_instance,
        )

    def get_fieldsets(self):
        return [
            { 'legend':_('HIERARCHY'), 'fields':self.get_fields('status','order','url') },
            { 'legend':_('CONTENT'), 'fields':
             self.get_fields('name','introduction','points_to_pass', 'model_answer') },
            { 'legend':_('REVEAL_MODEL_SOLUTIONS'), 'fields': self.model_solution_form },
            { 'legend':_('SCHEDULE'), 'fields':self.get_fields('reading_opening_time','opening_time','closing_time',
                'late_submissions_allowed','late_submission_deadline', 'late_submission_penalty') },
        ]

    def is_valid(self) -> bool:
        return (
            super().is_valid()
            and self.model_solution_form.is_valid()
        )

    def save(self, *args: Any, **kwargs: Any) -> Any:
        if self.model_solution_form.has_changed():
            self.instance.model_solution_reveal_rule = (
                self.model_solution_form.save(*args, **kwargs)
            )
        return super().save(*args, **kwargs)


class CourseInstanceForm(forms.ModelForm):

    teachers = UsersSearchSelectField(
        label=_('LABEL_TEACHERS'),
        queryset=UserProfile.objects.all(),
        initial_queryset=UserProfile.objects.none(),
        required=False)
    assistants = UsersSearchSelectField(
        label=_('LABEL_ASSISTANTS'),
        queryset=UserProfile.objects.all(),
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
            'teachers',
            'assistants',
            'technical_error_emails',
            'sis_enroll',
            'points_goal_enabled',
        ]
        widgets = {
            'starting_time': DateTimeLocalInput,
            'ending_time': DateTimeLocalInput,
            'lifesupport_time': DateTimeLocalInput,
            'archive_time': DateTimeLocalInput,
            'enrollment_starting_time': DateTimeLocalInput,
            'enrollment_ending_time': DateTimeLocalInput,
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields['teachers'].initial = self.instance.teachers.all()
        self.fields['teachers'].initial_queryset = self.instance.teachers.all()
        self.fields['teachers'].widget.search_api_url = api_reverse("user-list")
        self.fields['assistants'].initial = self.instance.assistants.all()
        self.fields['assistants'].initial_queryset = self.instance.assistants.all()
        self.fields['assistants'].widget.search_api_url = api_reverse("user-list")
        if self.instance and self.instance.visible_to_students:
            self.fields["url"].widget.attrs["readonly"] = "true"
            self.fields["url"].help_text = _('COURSE_URL_IDENTIFIER_LOCKED_WHILE_COURSE_VISIBLE')
            self.fields["lifesupport_time"].help_text = _('COURSE_REMOVES_MODEL_ANSWER_VISIBILITY_STUDENTS')
            self.fields["archive_time"].help_text = _('COURSE_REMOVES_SUBMISSION_POSSIBILITY_STUDENTS')

        # If course is not connected to SIS system, disable the enroll checkbox
        if not self.instance.sis_id:
            self.fields['sis_enroll'].disabled = True

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
        generate_url_key_validator()(self.cleaned_data['url'])
        url = self.cleaned_data['url']
        if url in self.instance.RESERVED_URLS:
            raise ValidationError(_('ERROR_URL_ALREADY_TAKEN'))
        if url != self.instance.url and CourseInstance.objects.filter(course=self.instance.course, url=url).exists():
            raise ValidationError(_('ERROR_URL_ALREADY_TAKEN'))
        return url

    def save(self, *args, **kwargs):
        self.instance.set_assistants(self.cleaned_data['assistants'])
        self.instance.set_teachers(self.cleaned_data['teachers'])

        if not self.instance.visible_to_students:
            for userprofile in self.instance.all_students:
                CachedNotifications.invalidate(userprofile.user)

        return super().save(*args, **kwargs)


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
    url = forms.CharField(
        label=_('COURSE_NEW_URL_IDENTIFIER_COURSE_INSTANCE'),
        help_text=_('COURSE_NEW_URL_IDENTIFIER_COURSE_INSTANCE_HELPTEXT'),
        max_length=255,
        validators=[generate_url_key_validator()],
    )
    instance_name = forms.CharField(
        label=_('LABEL_INSTANCE_NAME'),
        help_text=_('LABEL_INSTANCE_NAME_HELPTEXT'),
        max_length=255,
    )
    teachers = forms.BooleanField(
        label=_('LABEL_TEACHERS'),
        help_text=_('LABEL_TEACHERS_HELPTEXT'),
        required=False,
        initial=True,
    )
    assistants = forms.BooleanField(
        label=_('LABEL_ASSISTANTS'),
        help_text=_('LABEL_ASSISTANTS_HELPTEXT'),
        required=False,
        initial=True,
    )
    menuitems = forms.BooleanField(
        label=_('LABEL_MENU_ITEMS'),
        help_text=_('LABEL_MENU_ITEMS_HELPTEXT'),
        required=False,
        initial=True,
    )
    usertags = forms.BooleanField(
        label=_('LABEL_STUDENT_TAGS'),
        help_text=_('LABEL_STUDENT_TAGS_HELPTEXT'),
        required=False,
        initial=True,
    )
    submissiontags = forms.BooleanField(
        label=_('LABEL_SUBMISSION_TAGS'),
        help_text=_('LABEL_SUBMISSION_TAGS_HELPTEXT'),
        required=False,
        initial=True,
    )

    if settings.GITMANAGER_URL:
        key_year = forms.IntegerField(
            label=_('LABEL_YEAR'),
            help_text=_('LABEL_YEAR_HELPTEXT'),
            widget=forms.Select(choices=[
                (year, year) for year in range(timezone.now().year, timezone.now().year + 5)
            ]),
        )
        key_month = forms.CharField(
            label=_('LABEL_SEMESTER_OR_MONTH'),
            help_text=_('LABEL_SEMESTER_OR_MONTH_HELPTEXT'),
            widget=forms.Select(choices=[
                ('Autumn', _('LABEL_AUTUMN')),
                ('Spring', _('LABEL_SPRING')),
                ('Summer', _('LABEL_SUMMER')),
                ('January', _('LABEL_JANUARY')),
                ('February', _('LABEL_FEBRUARY')),
                ('March', _('LABEL_MARCH')),
                ('April', _('LABEL_APRIL')),
                ('May', _('LABEL_MAY')),
                ('June', _('LABEL_JUNE')),
                ('July', _('LABEL_JULY')),
                ('August', _('LABEL_AUGUST')),
                ('September', _('LABEL_SEPTEMBER')),
                ('October', _('LABEL_OCTOBER')),
                ('November', _('LABEL_NOVEMBER')),
                ('December', _('LABEL_DECEMBER')),
                ('Test', _('LABEL_TEST')),
            ]),
        )
        update_automatically = forms.BooleanField(
            label=_('LABEL_UPDATE_AUTOMATICALLY'),
            help_text=_('LABEL_UPDATE_AUTOMATICALLY_HELPTEXT'),
            required=False,
            initial=True,
        )
        email_on_error = forms.BooleanField(
            label=_('LABEL_EMAIL_ON_ERROR'),
            help_text=_('LABEL_EMAIL_ON_ERROR_HELPTEXT'),
            required=False,
            initial=True,
        )
        git_origin = forms.CharField(
            label=_('LABEL_GIT_ORIGIN'),
            help_text=_('LABEL_GIT_ORIGIN_HELPTEXT'),
            max_length=255,
            required=False,
        )
        git_branch = forms.CharField(
            label=_('LABEL_GIT_BRANCH'),
            help_text=_('LABEL_GIT_BRANCH_HELPTEXT'),
            max_length=40,
            required=False,
        )

    def set_sis_selector(self) -> None:
        sis: StudentInfoSystem = get_sis_configuration()
        if not sis:
            # Student Info System not configured
            return

        try:
            instances = sis.get_instances(self.instance.course.code)

            # If there are no SIS instances by this course code, don't show menu or checkbox
            if instances:
                options = [('none', '---------')] + instances
                self.fields['sis'] = forms.ChoiceField(
                        choices=options,
                        label=_('LABEL_SIS_INSTANCE'),
                        help_text=_('LABEL_SIS_INSTANCE_HELPTEXT'),
                )
                self.fields['sis_enroll'] = forms.BooleanField(
                    label=_('LABEL_SIS_ENROLL'),
                    help_text=_('LABEL_SIS_ENROLL_HELPTEXT'),
                    required=False,
                    initial=False,
                )
        except Exception:
            logger.exception("Error getting instances from SIS.")

    def set_initial_git_origin(self) -> None:
        permissions = Permissions()
        permissions.instances.add(Permission.READ, id=self.instance.id)
        gitmanager_url = urllib.parse.urljoin(settings.GITMANAGER_URL, f"api/gitmanager/id/{self.instance.id}")
        try:
            response = aplus_get(gitmanager_url, permissions=permissions)
            if response.status_code == 200:
                data = response.json()
                self.fields['git_origin'].initial = data.get('git_origin')
        except Exception:
            pass

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance')
        super().__init__(*args, **kwargs)
        self.fields['instance_name'].initial = self.instance.instance_name
        self.set_sis_selector()
        self.set_initial_git_origin()

    def clean_url(self):
        url = self.cleaned_data['url']
        if CourseInstance.objects.filter(
                course=self.instance.course, url=url).exists():
            raise ValidationError(_('ERROR_URL_ALREADY_TAKEN'))
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
        labels = {
            'name': _('LABEL_NAME'),
            'slug': _('LABEL_SLUG'),
            'description': _('LABEL_DESCRIPTION'),
            'color': _('LABEL_COLOR'),
        }

    @classmethod
    def get_base_object(self, course_instance):
        obj = self.Meta.model()
        obj.course_instance = course_instance
        return obj


class SubmissionTagForm(ColorTagForm):

    class Meta(ColorTagForm.Meta):
        model = SubmissionTag
        fields = [
            'name',
            'slug',
            'description',
            'color',
        ]
        labels = {
            'name': _('LABEL_NAME'),
            'slug': _('LABEL_SLUG'),
            'description': _('LABEL_DESCRIPTION'),
            'color': _('LABEL_COLOR'),
        }

    @classmethod
    def get_base_object(self, course_instance):
        obj = self.Meta.model()
        obj.course_instance = course_instance
        return obj


class SelectUsersForm(forms.Form):
    user = UsersSearchSelectField(queryset=UserProfile.objects.none(),
        initial_queryset=UserProfile.objects.none())

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        course_instance = kwargs.pop('instance')
        super().__init__(*args, **kwargs)
        self.fields['user'].widget.search_api_url = api_reverse(
            "course-students-list", kwargs={'course_id': course_instance.id})
        self.fields['user'].queryset = course_instance.get_student_profiles()


class GitmanagerForm(forms.Form):
    key = forms.SlugField(
        label=_('LABEL_KEY'),
        help_text=_('LABEL_KEY_HELPTEXT'),
    )
    update_automatically = forms.BooleanField(
        label=_('LABEL_UPDATE_AUTOMATICALLY'),
        help_text=_('LABEL_UPDATE_AUTOMATICALLY_HELPTEXT'),
        required=False,
    )
    email_on_error = forms.BooleanField(
        label=_('LABEL_EMAIL_ON_ERROR'),
        help_text=_('LABEL_EMAIL_ON_ERROR_HELPTEXT'),
        required=False,
    )
    git_origin = forms.CharField(
        label=_('LABEL_GIT_ORIGIN'),
        help_text=_('LABEL_GIT_ORIGIN_HELPTEXT'),
        max_length=255,
    )
    git_branch = forms.CharField(
        label=_('LABEL_GIT_BRANCH'),
        help_text=_('LABEL_GIT_BRANCH_HELPTEXT'),
        max_length=40,
    )
    update_hook = forms.URLField(
        label=_('LABEL_UPDATE_HOOK'),
        help_text=_('LABEL_UPDATE_HOOK_HELPTEXT'),
        required=False,
    )
    remote_id = forms.IntegerField(
        label=_('LABEL_ID'),
        help_text=_('LABEL_ID_HELPTEXT'),
        required=False,
        disabled=True,
    )
    # forms.CharField because forms.URLField validation fails for docker container addresses
    aplus_json_url = forms.CharField(
        label=_('LABEL_APLUS_CONFIGURATION_JSON'),
        help_text=_('LABEL_APLUS_CONFIGURATION_JSON_HELPTEXT'),
        required=False,
        disabled=True,
    )
    # forms.CharField because forms.URLField validation fails for docker container addresses
    hook = forms.CharField(
        label=_('LABEL_HOOK'),
        help_text=_('LABEL_HOOK_HELPTEXT'),
        required=False,
        disabled=True,
    )
    webhook_secret = forms.CharField(
        label=_('LABEL_WEBHOOK_SECRET'),
        help_text=_('LABEL_WEBHOOK_SECRET_HELPTEXT'),
        max_length=64,
        required=False,
        disabled=True,
    )

    def set_initial_values(self):
        self.fields['remote_id'].initial = self.instance.id
        self.fields['aplus_json_url'].initial = self.instance.configure_url
        self.fields['update_automatically'].initial = True
        self.fields['email_on_error'].initial = True
        permissions = Permissions()
        permissions.instances.add(Permission.READ, id=self.instance.id)
        # Write access is needed to retrieve the webhook secret
        permissions.instances.add(Permission.WRITE, id=self.instance.id)
        gitmanager_url = urllib.parse.urljoin(settings.GITMANAGER_URL, f"api/gitmanager/id/{self.instance.id}")
        try:
            response = aplus_get(gitmanager_url, permissions=permissions)
            if response.status_code == 200:
                data = response.json()
                key = data.get('key')
                self.fields['key'].initial = key
                self.fields['update_automatically'].initial = data.get('update_automatically')
                self.fields['email_on_error'].initial = data.get('email_on_error')
                self.fields['git_origin'].initial = data.get('git_origin')
                self.fields['git_branch'].initial = data.get('git_branch')
                self.fields['update_hook'].initial = data.get('update_hook')
                self.fields['webhook_secret'].initial = data.get('webhook_secret')
                self.fields['hook'].initial = urllib.parse.urljoin(settings.GITMANAGER_URL, f"gitmanager/{key}/hook")
        except Exception:
            pass

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance')
        super().__init__(*args, **kwargs)
        self.set_initial_values()
