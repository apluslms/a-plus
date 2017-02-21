from django.contrib import admin

from .models import (
    Threshold,
    ThresholdPoints,
    CourseModuleRequirement,
)


class ThresholdPointsInline(admin.TabularInline):
    model = ThresholdPoints


class ThresholdAdmin(admin.ModelAdmin):
    list_display_links = ("id", "__str__")
    list_display = ("id", "course_instance", "__str__")
    list_filter = ("course_instance",)
    inlines = (ThresholdPointsInline,)


class CourseModuleRequirementAdmin(admin.ModelAdmin):
    list_display_links = ("id", "__str__")
    list_display = ("id", "get_course", "module", "__str__")

    def get_course(self, obj):
        return obj.module.course_instance
    get_course.short_description = "Course instance"

admin.site.register(Threshold, ThresholdAdmin)
admin.site.register(CourseModuleRequirement, CourseModuleRequirementAdmin)
