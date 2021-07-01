from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from exercise.models import (
    CourseChapter,
    BaseExercise,
    StaticExercise,
    ExerciseWithAttachment,
    Submission,
    SubmittedFile,
)
from exercise.exercisecollection_models import ExerciseCollection


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
    return ", ".join([
        "{} ({})".format(
            p.user.get_full_name(),
            p.student_id or p.user.username,
        ) for p in obj.submitters.all()
    ])


real_class.short_description = _('REAL_CLASS')
course_wrapper.short_description = _('COURSE_INSTANCE')
submitters_wrapper.short_description = _('SUBMITTERS')


class CourseChapterAdmin(admin.ModelAdmin):
    search_fields = (
        'name',
        'category__name',
        'course_module__name',
        'course_module__course_instance__instance_name',
    )
    list_display_links = ('__str__',)
    list_display = (
        'course_instance',
        '__str__',
        'service_url',
    )
    list_filter = (
        'course_module__course_instance',
        'course_module',
    )


class BaseExerciseAdmin(admin.ModelAdmin):
    search_fields = (
        'name',
        'category__name',
        'course_module__name',
        'course_module__course_instance__instance_name',
    )
    list_display_links = ('__str__',)
    list_display = (
        'course_instance',
        '__str__',
        'max_points',
        real_class,
    )
    list_filter = (
        'course_module__course_instance',
        'course_module',
    )


class SubmissionAdmin(admin.ModelAdmin):
    search_fields = (
        'exercise__name',
        'submitters__student_id',
        'submitters__user__username',
        'submitters__user__first_name',
        'submitters__user__last_name',
        'submitters__user__email',
    )
    list_display_links = ('id',)
    list_display = (
        'id',
        'exercise',
        course_wrapper,
        submitters_wrapper,
        'status',
        'grade',
        'submission_time',
    )
    list_filter = (
        'status',
        'grade',
        'submission_time',
        'exercise__course_module__course_instance',
    )
    search_fields = (
        'id',
        'exercise__name',
        'exercise__course_module__course_instance__instance_name',
        'submitters__student_id',
        'submitters__user__username',
        'submitters__user__first_name',
        'submitters__user__last_name',
        'submitters__user__email',
    )
    list_per_page = 500
    raw_id_fields = (
        'submitters',
        'grader',
    )
    readonly_fields = ('submission_time',)

    def get_queryset(self, request):
        return super().get_queryset(request)\
            .defer('feedback', 'assistant_feedback',
                'submission_data', 'grading_data')\
            .prefetch_related('submitters')


class SubmittedFileAdmin(admin.ModelAdmin):
    search_fields = (
        'submission__exercise__name',
        'submission__submitters__student_id',
        'submission__submitters__user__username',
        'submission__submitters__user__first_name',
        'submission__submitters__user__last_name',
        'submission__submitters__user__email',
    )


class StaticExerciseAdmin(admin.ModelAdmin):
    search_fields = (
        'name',
        'category__name',
        'course_module__name',
        'course_module__course_instance__instance_name',
    )


class ExerciseWithAttachmentAdmin(admin.ModelAdmin):
    search_fields = (
        'name',
        'category__name',
        'course_module__name',
        'course_module__course_instance__instance_name',
    )


class ExerciseCollectionAdmin(admin.ModelAdmin):
    search_fields = (
        'name',
        'category__name',
        'course_module__name',
        'course_module__course_instance__instance_name',
    )


class ExerciseCollectionExerciseAdmin(admin.ModelAdmin):
    list_display_links = ('__str__',)
    list_display = (
        'course_instance',
        '__str__',
        'max_points',
        'target_category',
    )
    list_filter = (
        'course_module___course_instance',
        'course_module',
    )
    fields = (
        'target_category',
        'max_points',
    )


admin.site.register(CourseChapter, CourseChapterAdmin)
admin.site.register(BaseExercise, BaseExerciseAdmin)
admin.site.register(StaticExercise, StaticExerciseAdmin)
admin.site.register(ExerciseWithAttachment, ExerciseWithAttachmentAdmin)
admin.site.register(Submission, SubmissionAdmin)
admin.site.register(SubmittedFile, SubmittedFileAdmin)
admin.site.register(ExerciseCollection, ExerciseCollectionAdmin)
