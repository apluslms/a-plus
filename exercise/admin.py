from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from exercise.models import CourseModule, LearningObjectCategory, \
    BaseExercise, StaticExercise, ExerciseWithAttachment, \
    DeadlineRuleDeviation, MaxSubmissionsRuleDeviation, \
    Submission, SubmittedFile
from exercise.templatetags import exercise_info


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
    return exercise_info.students(obj.submitters.all())


real_class.short_description = _('Real class')
course_wrapper.short_description = _('Course instance')
submitters_wrapper.short_description = _('Submitters')


class CourseModuleAdmin(admin.ModelAdmin):
    list_display_links = ("name",)
    list_display = ("name", "course_instance", "opening_time", "closing_time")
    list_filter = ["course_instance", "opening_time", "closing_time"]


class LearningObjectCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "course_instance"]
    list_filter = ["course_instance"]
    ordering = ["course_instance", "id"]


class BaseExerciseAdmin(admin.ModelAdmin):
    list_display_links = ["name"]
    list_display = ["name", "course_module", "max_points", real_class]
    list_filter = ["course_module__course_instance", "course_module"]

    class Media:
        js = ('/static/tiny_mce/tiny_mce.js',
              '/static/js/tiny_mce_textareas.js',)


class StaticExerciseAdmin(admin.ModelAdmin):
    pass


class ExerciseWithAttachmentAdmin(admin.ModelAdmin):
    pass


class DeadlineRuleDeviationAdmin(admin.ModelAdmin):
    list_display = ["submitter", "exercise", "extra_minutes", ]
    list_filter = ["exercise__course_module__course_instance"]


class MaxSubmissionsRuleDeviationAdmin(admin.ModelAdmin):
    pass


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


class SubmittedFileAdmin(admin.ModelAdmin):
    pass


admin.site.register(CourseModule, CourseModuleAdmin)
admin.site.register(LearningObjectCategory, LearningObjectCategoryAdmin)
admin.site.register(BaseExercise, BaseExerciseAdmin)
admin.site.register(StaticExercise, StaticExerciseAdmin)
admin.site.register(ExerciseWithAttachment, ExerciseWithAttachmentAdmin)
admin.site.register(DeadlineRuleDeviation, DeadlineRuleDeviationAdmin)
admin.site.register(MaxSubmissionsRuleDeviation,
                    MaxSubmissionsRuleDeviationAdmin)
admin.site.register(Submission, SubmissionAdmin)
admin.site.register(SubmittedFile, SubmittedFileAdmin)
