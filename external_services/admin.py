from django.contrib import admin

from external_services.models import LTIService, LTI1p3Service, LinkService, MenuItem
from lib.admin_helpers import RecentCourseInstanceListFilter


@admin.register(LinkService)
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


@admin.register(LTIService)
class LTIServiceAdmin(LinkServiceAdmin):
    search_fields = LinkServiceAdmin.search_fields + ('consumer_key',)
    list_display = LinkServiceAdmin.list_display + ('access_settings',)


@admin.register(LTI1p3Service)
class LTI1p3ServiceAdmin(LinkServiceAdmin):
    search_fields = LinkServiceAdmin.search_fields + ('login_url',)
    list_display = LinkServiceAdmin.list_display + ('client_id',)


@admin.register(MenuItem)
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
