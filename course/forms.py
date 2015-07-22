from django import forms
from course.models import CourseModule, CourseChapter


class CourseModuleForm(forms.ModelForm):

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


class CourseChapterForm(forms.ModelForm):

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
