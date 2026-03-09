from django.contrib import admin

from .models import (
    BaseTab,
    HTMLTab,
    ExternalEmbeddedTab,
    ExternalIFrameTab,
    BasePlugin,
    RSSPlugin,
    HTMLPlugin,
    ExternalIFramePlugin,
)


@admin.register(BaseTab)
class BaseTabAdmin(admin.ModelAdmin):
    search_fields = (
        'label',
        'title',
    )


@admin.register(HTMLTab)
class HTMLTabAdmin(admin.ModelAdmin):
    search_fields = (
        'label',
        'title',
    )


@admin.register(ExternalEmbeddedTab)
class ExternalEmbeddedTabAdmin(admin.ModelAdmin):
    search_fields = (
        'label',
        'title',
        'content_url',
    )


@admin.register(ExternalIFrameTab)
class ExternalIFrameTabAdmin(admin.ModelAdmin):
    search_fields = (
        'label',
        'title',
        'content_url',
    )


@admin.register(BasePlugin)
class BasePluginAdmin(admin.ModelAdmin):
    search_fields = ('title',)


@admin.register(RSSPlugin)
class RSSPluginAdmin(admin.ModelAdmin):
    search_fields = (
        'title',
        'feed_url',
    )


@admin.register(HTMLPlugin)
class HTMLPluginAdmin(admin.ModelAdmin):
    search_fields = ('title',)
    list_display_links = ('title',)
    list_display = (
        'title',
        'course_instance_id',
        'container_type',
        'views',
    )

    def course_instance_id(self, obj):
        return obj.container_pk


@admin.register(ExternalIFramePlugin)
class ExternalIFramePluginAdmin(admin.ModelAdmin):
    search_fields = (
        'title',
        'service_url',
    )


