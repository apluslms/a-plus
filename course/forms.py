from django import forms
from course.models import LearningObjectCategory, CourseModule, CourseChapter


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
        super(CourseChapterForm, self).__init__(*args, **kwargs)
        self.chapter = kwargs.get('instance')
        self.fields["course_module"].queryset = CourseModule.objects.filter(
            course_instance=self.chapter.course_instance)
