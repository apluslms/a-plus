from django.contrib import admin

from lib.admin_helpers import RecentCourseInstanceListFilter
from .models import News


class NewsAdmin(admin.ModelAdmin):
    search_fields = (
        "course_instance__instance_name",
        "course_instance__course__code",
        "course_instance__course__name",
        "title",
    )
    list_display_links = ("title",)
    list_display = (
        "course_instance",
        "title",
        "publish",
        "audience",
        "pin",
    )
    list_filter = (
        RecentCourseInstanceListFilter,
        "publish",
    )
    raw_id_fields = ("course_instance",)


admin.site.register(News, NewsAdmin)
