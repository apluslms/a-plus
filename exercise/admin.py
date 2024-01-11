from typing import Optional, Sequence, Tuple

from django.contrib import admin
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from django.utils.translation import gettext_lazy as _

from exercise.models import (
    CourseChapter,
    BaseExercise,
    StaticExercise,
    ExerciseWithAttachment,
    LTIExercise,
    LTI1p3Exercise,
    Submission,
    SubmissionDraft,
    SubmittedFile,
    RevealRule,
    ExerciseTask,
    LearningObjectDisplay,
    PendingSubmission,
)
from exercise.exercisecollection_models import ExerciseCollection
from lib.admin_helpers import make_column_link, RecentCourseInstanceListFilter


def real_class(obj):
    """
    Returns the leaf class name of an exercise.
    """
    return obj.content_type.model_class().__name__


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


class GradeListFilter(admin.SimpleListFilter):
    title = _('LABEL_GRADE')
    parameter_name = 'grade'

    def lookups(self, request: HttpRequest, model_admin: admin.ModelAdmin) -> Sequence[Tuple[str, str]]:
        return [
            ('grade__exact=0', '0'),
            ('grade__exact=1', '1'),
            ('grade__exact=2', '2'),
            ('grade__lt=10', '< 10'),
            ('grade__gte=10', '>= 10'),
            ('grade__lt=20', '< 20'),
            ('grade__gte=20', '>= 20'),
            ('grade__lt=50', '< 50'),
            ('grade__gte=50', '>= 50'),
            ('grade__lt=100', '< 100'),
            ('grade__gte=100', '>= 100'),
            ('grade__lt=150', '< 150'),
            ('grade__gte=150', '>= 150'),
            ('grade__lt=200', '< 200'),
            ('grade__gte=200', '>= 200'),
        ]
    # pylint: disable-next=inconsistent-return-statements
    def queryset(self, request: HttpRequest, queryset: QuerySet) -> Optional[QuerySet]:
        lookup = self.value()
        if not lookup:
            return
        lookup = lookup.split('=', 1)
        q = {lookup[0]: lookup[1]}
        return queryset.filter(**q)


class SubmissionRecentCourseInstanceListFilter(RecentCourseInstanceListFilter):
    course_instance_query = 'exercise__course_module__course_instance'

class LearningObjectRecentCourseInstanceListFilter(RecentCourseInstanceListFilter):
    course_instance_query = 'course_module__course_instance'

class SubmittedFileRecentCourseInstanceListFilter(RecentCourseInstanceListFilter):
    course_instance_query = 'submission__exercise__course_module__course_instance'


class CourseChapterAdmin(admin.ModelAdmin):
    search_fields = (
        'name',
        'category__name',
        'course_module__name',
        'course_module__course_instance__instance_name',
        'course_module__course_instance__course__code',
        'course_module__course_instance__course__name',
    )
    list_display_links = ('__str__',)
    list_display = (
        'course_instance',
        'course_module',
        '__str__',
        'service_url',
    )
    list_filter = (
        'course_module__opening_time',
        'course_module__closing_time',
        LearningObjectRecentCourseInstanceListFilter,
    )
    raw_id_fields = (
        'category',
        'course_module',
        'parent',
    )


class BaseExerciseAdmin(admin.ModelAdmin):
    search_fields = (
        'name',
        'category__name',
        'course_module__name',
        'course_module__course_instance__instance_name',
        'course_module__course_instance__course__code',
        'course_module__course_instance__course__name',
    )
    list_display_links = ('__str__',)
    list_display = (
        'course_instance',
        'course_module',
        '__str__',
        'max_points',
        real_class,
    )
    list_filter = (
        'course_module__opening_time',
        'course_module__closing_time',
        LearningObjectRecentCourseInstanceListFilter,
    )
    raw_id_fields = (
        'category',
        'course_module',
        'parent',
        'submission_feedback_reveal_rule',
        'model_solutions_reveal_rule',
    )


class SubmissionAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = (
        'id',
        'exercise',
        course_wrapper,
        submitters_wrapper,
        'status',
        'unofficial_submission_type',
        'grade',
        'submission_time',
    )
    list_filter = (
        'status',
        'submission_time',
        SubmissionRecentCourseInstanceListFilter,
        GradeListFilter,
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
    list_per_page = 100
    raw_id_fields = (
        'submitters',
        'grader',
        'exercise',
    )
    readonly_fields = ('submission_time',)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('submitters')


class SubmissionDraftAdmin(admin.ModelAdmin):
    search_fields = (
        'id',
        'exercise__name',
        'exercise__course_module__course_instance__instance_name',
        'submitter__student_id',
        'submitter__user__username',
        'submitter__user__first_name',
        'submitter__user__last_name',
        'submitter__user__email',
    )
    list_display_links = (
        'id',
        'exercise',
    )
    list_display = (
        'id',
        'exercise',
        course_wrapper,
        'submitter',
        'active',
        'timestamp',
    )
    list_filter = (
        'active',
        'timestamp',
        SubmissionRecentCourseInstanceListFilter,
    )
    list_per_page = 300
    raw_id_fields = (
        'submitter',
        'exercise',
    )
    readonly_fields = ('timestamp',)

    def get_queryset(self, request: HttpRequest) -> QuerySet[SubmissionDraft]:
        return (
            super().get_queryset(request)
            .defer('submission_data')
            .prefetch_related('exercise', 'submitter')
        )


class SubmittedFileAdmin(admin.ModelAdmin):
    search_fields = (
        'submission__exercise__name',
        'submission__submitters__student_id',
        'submission__submitters__user__username',
        'submission__submitters__user__first_name',
        'submission__submitters__user__last_name',
        'submission__submitters__user__email',
    )
    list_display = (
        'get_course_instance',
        'get_exercise',
        'submission',
        'get_submitters',
        'param_name',
    )
    list_display_links = (
        'submission',
        'get_submitters',
        'param_name',
    )
    list_filter = (
        SubmittedFileRecentCourseInstanceListFilter,
    )
    raw_id_fields = ('submission',)

    @admin.display(description=_('LABEL_COURSE_INSTANCE'))
    def get_course_instance(self, obj):
        return str(obj.submission.exercise.course_module.course_instance)

    @admin.display(description=_('LABEL_EXERCISE'))
    def get_exercise(self, obj):
        return str(obj.submission.exercise)

    @admin.display(description=_('LABEL_SUBMITTERS'))
    def get_submitters(self, obj):
        return ', '.join(str(s) for s in obj.submission.submitters.all())


class StaticExerciseAdmin(admin.ModelAdmin):
    search_fields = (
        'name',
        'category__name',
        'course_module__name',
        'course_module__course_instance__instance_name',
    )
    list_display = (
        'course_instance',
        'course_module',
        '__str__',
        'max_points',
    )
    list_display_links = (
        '__str__',
    )
    raw_id_fields = (
        'category',
        'course_module',
        'parent',
        'submission_feedback_reveal_rule',
        'model_solutions_reveal_rule',
    )


class ExerciseWithAttachmentAdmin(admin.ModelAdmin):
    search_fields = (
        'name',
        'category__name',
        'course_module__name',
        'course_module__course_instance__instance_name',
    )
    list_display = (
        'course_instance',
        'course_module',
        '__str__',
        'max_points',
    )
    list_display_links = (
        '__str__',
    )
    raw_id_fields = (
        'course_module',
        'category',
        'parent',
        'submission_feedback_reveal_rule',
        'model_solutions_reveal_rule',
    )


class LTIExerciseAdmin(admin.ModelAdmin):
    search_fields = (
        'name',
        'category__name',
        'course_module__name',
        'course_module__course_instance__instance_name',
        'course_module__course_instance__course__code',
        'course_module__course_instance__course__name',
    )
    list_display_links = ('__str__',)
    list_display = (
        'course_instance',
        'course_module',
        '__str__',
        'max_points',
        real_class,
    )
    list_filter = (
        LearningObjectRecentCourseInstanceListFilter,
    )
    raw_id_fields = (
        'category',
        'course_module',
        'lti_service',
        'parent',
        'submission_feedback_reveal_rule',
        'model_solutions_reveal_rule',
    )


class LTI1p3ExerciseAdmin(admin.ModelAdmin):
    search_fields = (
        'name',
        'category__name',
        'course_module__name',
        'course_module__course_instance__instance_name',
        'course_module__course_instance__course__code',
        'course_module__course_instance__course__name',
    )
    list_display_links = ('__str__',)
    list_display = (
        'course_instance',
        'course_module',
        '__str__',
        'max_points',
    )
    list_filter = (
        LearningObjectRecentCourseInstanceListFilter,
    )
    raw_id_fields = (
        'category',
        'course_module',
        'lti_service',
        'parent',
        'submission_feedback_reveal_rule',
        'model_solutions_reveal_rule',
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


class RevealRuleAdmin(admin.ModelAdmin):
    search_fields = (
        'trigger',
    )
    list_display_links = ('__str__',)
    list_display = (
        '__str__',
        'trigger',
        'delay_minutes',
        'time',
        'currently_revealed',
    )

class ExerciseTaskAdmin(admin.ModelAdmin):
    search_fields = (
        'task_id',
        'exercise__name',
        'exercise__course_module__course_instance__instance_name',
        'exercise__course_module__course_instance__course__code',
        'exercise__course_module__course_instance__course__name',
    )
    list_display = (
        'get_course',
        'exercise',
        'task_type',
        'task_id',
    )
    list_display_links = (
        'task_type',
        'task_id',
    )
    raw_id_fields = ('exercise',)

    def get_course(self, obj):
        return str(obj.exercise.course_module.course_instance)


class LearningObjectDisplayAdmin(admin.ModelAdmin):
    search_fields = (
        'learning_object__name',
        'learning_object__category__name',
        'learning_object__course_module__name',
        'learning_object__course_module__course_instance__instance_name',
        'learning_object__course_module__course_instance__course__code',
        'learning_object__course_module__course_instance__course__name',
    )
    list_display = (
        'learning_object',
        'profile',
        'timestamp',
    )
    raw_id_fields = (
        'learning_object',
        'profile',
    )
    readonly_fields = ('timestamp',)


class PendingSubmissionAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = (
        'id',
        'course_instance_link',
        'exercise_link',
        'submission_link',
        'submission_time',
        'num_retries',
        'submission_status',
    )
    list_filter = (
        'submission__status',
        'submission_time',
    )
    search_fields = (
        'id',
        'submission__exercise__name',
        'submission__exercise__course_module__course_instance__instance_name',
        'submission__submitters__student_id',
        'submission__submitters__user__username',
        'submission__submitters__user__first_name',
        'submission__submitters__user__last_name',
        'submission__submitters__user__email',
    )
    raw_id_fields = (
        'submission',
    )

    @admin.display(description=_('LABEL_SUBMISSION'))
    def submission_link(self, pending_submission):
        return make_column_link(
            pending_submission.submission,
            'admin:exercise_submission_change',
        )

    @admin.display(description=_('LABEL_COURSE_INSTANCE'))
    def course_instance_link(self, pending_submission):
        return make_column_link(
            pending_submission.submission.exercise.course_module.course_instance,
            'admin:course_courseinstance_change',
        )

    @admin.display(description=_('LABEL_EXERCISE'))
    def exercise_link(self, pending_submission):
        return make_column_link(
            pending_submission.submission.exercise,
            'admin:exercise_baseexercise_change',
        )

    @admin.display(description=_('LABEL_STATUS'))
    def submission_status(self, pending_submission):
        return Submission.STATUS[pending_submission.submission.status]


admin.site.register(CourseChapter, CourseChapterAdmin)
admin.site.register(BaseExercise, BaseExerciseAdmin)
admin.site.register(StaticExercise, StaticExerciseAdmin)
admin.site.register(ExerciseWithAttachment, ExerciseWithAttachmentAdmin)
admin.site.register(LTIExercise, LTIExerciseAdmin)
admin.site.register(LTI1p3Exercise, LTI1p3ExerciseAdmin)
admin.site.register(Submission, SubmissionAdmin)
admin.site.register(SubmissionDraft, SubmissionDraftAdmin)
admin.site.register(SubmittedFile, SubmittedFileAdmin)
admin.site.register(ExerciseCollection, ExerciseCollectionAdmin)
admin.site.register(RevealRule, RevealRuleAdmin)
admin.site.register(ExerciseTask, ExerciseTaskAdmin)
admin.site.register(LearningObjectDisplay, LearningObjectDisplayAdmin)
admin.site.register(PendingSubmission, PendingSubmissionAdmin)
