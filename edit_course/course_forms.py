from django import forms
from django.utils.translation import ugettext_lazy as _

from course.models import LearningObjectCategory, CourseModule, \
    CourseChapter, CourseInstance


class FieldsetModelForm(forms.ModelForm):

    class Meta:
        fields = []

    def get_fieldsets(self):
        return [
            {
                "legend": "",
                "fields": [self[kw] for kw in self.Meta.fields]
            }
        ]


class LearningObjectCategoryForm(FieldsetModelForm):

    class Meta:
        model = LearningObjectCategory
        fields = [
            'name',
            'points_to_pass',
            'description'
        ]


class CourseModuleForm(FieldsetModelForm):

    class Meta:
        model = CourseModule
        fields = [
            'order',
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


class CourseChapterForm(FieldsetModelForm):

    class Meta:
        model = CourseChapter
        fields = [
            'course_module',
            'order',
            'name',
            'url',
            'content_url'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chapter = kwargs.get('instance')
        self.fields["course_module"].queryset = CourseModule.objects.filter(
            course_instance=self.chapter.course_instance)


class CourseInstanceForm(forms.ModelForm):

    class Meta:
        model = CourseInstance
        fields = [
            'visible_to_students',
            'instance_name',
            'url',
            'starting_time',
            'ending_time',
            'assistants'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assistants"].widget.attrs["class"] = "search-select"
        if self.instance and self.instance.visible_to_students:
            self.fields["url"].widget.attrs["readonly"] = "true"
            self.fields["url"].help_text = _("The URL identifier is locked "
                "while the course is visible to students.")

    def clean_url(self):
        if self.instance and self.instance.visible_to_students:
            return self.instance.url
        return self.cleaned_data["url"]
