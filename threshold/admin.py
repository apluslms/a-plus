from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from lib.admin_helpers import RecentCourseInstanceListFilter
from .models import (
    Threshold,
    ThresholdPoints,
    CourseModuleRequirement,
)


class CourseModuleRequirementRecentCourseInstanceListFilter(RecentCourseInstanceListFilter):
    course_instance_query = 'module__course_instance'


class ThresholdPointsInline(admin.TabularInline):
    model = ThresholdPoints


class ThresholdAdmin(admin.ModelAdmin):
    search_fields = (
        'name',
        'course_instance__instance_name',
        'course_instance__course__code',
        'course_instance__course__name',
    )
    list_display_links = (
        'id',
        '__str__',
    )
    list_display = (
        'id',
        'course_instance',
        '__str__',
        'consume_harder_points',
    )
    list_filter = (
        RecentCourseInstanceListFilter,
        'consume_harder_points',
    )
    inlines = (ThresholdPointsInline,)
    raw_id_fields = (
        'course_instance',
        'passed_modules',
        'passed_categories',
        'passed_exercises',
    )


class CourseModuleRequirementAdmin(admin.ModelAdmin):
    search_fields = (
        'module__name',
        'module__course_instance__instance_name',
        'module__course_instance__course__code',
        'module__course_instance__course__name',
        'threshold__name',
    )
    list_display_links = (
        'id',
        '__str__',
    )
    list_display = (
        'id',
        'get_course',
        'module',
        '__str__',
        'threshold',
    )
    list_filter = (
        CourseModuleRequirementRecentCourseInstanceListFilter,
        ('threshold', admin.RelatedOnlyFieldListFilter),
        'negative',
    )
    raw_id_fields = (
        'module',
        'threshold',
    )

    @admin.display(description=_('LABEL_COURSE_INSTANCE'))
    def get_course(self, obj):
        return str(obj.module.course_instance)


admin.site.register(Threshold, ThresholdAdmin)
admin.site.register(CourseModuleRequirement, CourseModuleRequirementAdmin)
