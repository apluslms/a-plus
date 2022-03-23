from django.contrib import admin

from deviations.models import DeadlineRuleDeviation, MaxSubmissionsRuleDeviation
from lib.admin_helpers import RecentCourseInstanceListFilter


class DeviationRecentCourseInstanceListFilter(RecentCourseInstanceListFilter):
    course_instance_query = 'exercise__course_module__course_instance'


class DeadlineRuleDeviationAdmin(admin.ModelAdmin):
    search_fields = (
        'submitter__student_id',
        'submitter__user__username',
        'submitter__user__first_name',
        'submitter__user__last_name',
        'submitter__user__email',
        'exercise__name',
    )
    list_display = (
        'submitter',
        'exercise',
        'extra_minutes',
        'granter',
        'grant_time',
    )
    list_filter = (
        DeviationRecentCourseInstanceListFilter,
    )
    raw_id_fields = (
        'exercise',
        'submitter',
        'granter',
    )
    readonly_fields = ('grant_time',)


class MaxSubmissionsRuleDeviationAdmin(admin.ModelAdmin):
    search_fields = (
        'submitter__student_id',
        'submitter__user__username',
        'submitter__user__first_name',
        'submitter__user__last_name',
        'submitter__user__email',
        'exercise__name',
    )
    list_display = (
        'submitter',
        'exercise',
        'extra_submissions',
        'granter',
        'grant_time',
    )
    list_filter = (
        DeviationRecentCourseInstanceListFilter,
    )
    raw_id_fields = (
        'exercise',
        'submitter',
        'granter',
    )
    readonly_fields = ('grant_time',)


admin.site.register(DeadlineRuleDeviation, DeadlineRuleDeviationAdmin)
admin.site.register(MaxSubmissionsRuleDeviation, MaxSubmissionsRuleDeviationAdmin)
