from django.contrib import admin

from .models import News


class NewsAdmin(admin.ModelAdmin):
    search_fields = ["course_instance__instance_name", "title"]
    list_display_links = ("title",)
    list_display = (
        "course_instance",
        "title",
        "publish",
        "audience",
        "pin",
    )
    list_filter = ("course_instance",)


admin.site.register(News, NewsAdmin)
