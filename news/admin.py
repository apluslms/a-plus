from django.contrib import admin

from .models import News


class NewsAdmin(admin.ModelAdmin):
    list_display_links = ("title",)
    list_display = (
        "course_instance",
        "title",
        "publish",
        "audience",
        "pin",
        "alert"
    )
    list_filter = ("course_instance",)


admin.site.register(News, NewsAdmin)
