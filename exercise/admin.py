from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from exercise.models import BaseExercise, StaticExercise, \
    ExerciseWithAttachment, Submission, SubmittedFile
from course.templatetags import course as coursetags


def real_class(obj):
    """
    Returns the leaf class name of an exercise.
    """
    return obj.as_leaf_class().__class__.__name__


def course_wrapper(obj):
    """
    Course instance for a submission.
    """
    return obj.exercise.course_module.course_instance


def submitters_wrapper(obj):
    """
    Submitters as a string for a submission.
    """
    return coursetags.profiles(obj.submitters.all())


real_class.short_description = _('Real class')
course_wrapper.short_description = _('Course instance')
submitters_wrapper.short_description = _('Submitters')


class BaseExerciseAdmin(admin.ModelAdmin):
    list_display_links = ["__str__"]
    list_display = ["__str__", "course_module", "course_instance",
                    "max_points", real_class]
    list_filter = ["course_module__course_instance", "course_module"]

    class Media:
        js = ('/static/tiny_mce/tiny_mce.js',
              '/static/js/tiny_mce_textareas.js',)


class SubmissionAdmin(admin.ModelAdmin):
    list_display_links = ("id",)
    list_display = ("id", "exercise", course_wrapper, submitters_wrapper,
                    "status", "grade", "submission_time")
    list_filter = ["exercise", "status", "grade", "submission_time",
                   "exercise__course_module__course_instance",
                   "exercise__course_module", "submitters__user__username"]
    search_fields = ["id", "exercise__name",
                     "exercise__course_module__course_instance__instance_name",
                     "submitters__student_id", "submitters__user__username",
                     "submitters__user__first_name",
                     "submitters__user__last_name", "submitters__user__email"]
    list_per_page = 500

    def get_queryset(self, request):
        return super().get_queryset(request)\
            .defer("feedback", "assistant_feedback",
                "submission_data", "grading_data")\
            .prefetch_related('submitters')


admin.site.register(BaseExercise, BaseExerciseAdmin)
admin.site.register(StaticExercise)
admin.site.register(ExerciseWithAttachment)
admin.site.register(Submission, SubmissionAdmin)
admin.site.register(SubmittedFile)
