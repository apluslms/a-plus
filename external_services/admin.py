from django.contrib import admin

from external_services.models import LTIService, LinkService, MenuItem
from lib.admin_helpers import RecentCourseInstanceListFilter


class LinkServiceAdmin(admin.ModelAdmin):
    search_fields = (
        'url',
        'menu_label',
    )
    list_display_links = (
        'id',
        'menu_label',
    )
    list_display = (
        'id',
        'menu_label',
        'url',
        'destination_region',
        'content_type',
        'enabled',
        'privacy_notice_url',
    )
    list_filter = (
        'enabled',
    )
    readonly_fields = ('content_type',)


class LTIServiceAdmin(LinkServiceAdmin):
    search_fields = LinkServiceAdmin.search_fields + ('consumer_key',)
    list_display = LinkServiceAdmin.list_display + ('access_settings',)


class MenuItemAdmin(admin.ModelAdmin):
    search_fields = (
        'course_instance__instance_name',
        'course_instance__course__code',
        'course_instance__course__name',
        'menu_url',
        'menu_label',
        'service__menu_label',
        'service__url',
    )
    list_display_links = (
        'id',
        'menu_label',
    )
    list_display = (
        'id',
        'course_instance',
        'service',
        'menu_url',
        'menu_label',
        'access',
        'enabled',
    )
    list_filter = (
        'enabled',
        'service',
        RecentCourseInstanceListFilter,
    )
    raw_id_fields = (
        'course_instance',
        'service',
    )


admin.site.register(LTIService, LTIServiceAdmin)
admin.site.register(LinkService, LinkServiceAdmin)
admin.site.register(MenuItem, MenuItemAdmin)
