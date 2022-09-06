from django.contrib import admin

from lib.admin_helpers import RecentCourseInstanceListFilter
from notification.models import Notification


class NotificationAdmin(admin.ModelAdmin):
    search_fields = (
        'subject',
        'sender__user__first_name',
        'sender__user__last_name',
        'recipient__user__first_name',
        'recipient__user__last_name',
        'recipient__student_id',
        'course_instance__course__name',
        'course_instance__course__code',
        'course_instance__instance_name',
    )
    list_display = (
        'course_instance',
        'subject',
        'sender',
        'recipient',
        'timestamp',
        'submission',
        'seen',
    )
    list_display_links = (
        'course_instance',
        'sender',
        'subject',
    )
    list_filter = (
        'seen',
        'timestamp',
        RecentCourseInstanceListFilter,
    )
    raw_id_fields = (
        'sender',
        'recipient',
        'course_instance',
        'submission',
    )
    readonly_fields = ('timestamp',)


admin.site.register(Notification, NotificationAdmin)
