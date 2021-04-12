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

class BaseTabAdmin(admin.ModelAdmin):
    search_fields = ["label", "title"]


class HTMLTabAdmin(admin.ModelAdmin):
    search_fields = ["label", "title"]


class ExternalEmbeddedTabAdmin(admin.ModelAdmin):
    search_fields = ["label", "title", "content_url"]


class ExternalIFrameTabAdmin(admin.ModelAdmin):
    search_fields = ["label", "title", "content_url"]


class BasePluginAdmin(admin.ModelAdmin):
    search_fields = ["title"]


class RSSPluginAdmin(admin.ModelAdmin):
    search_fields = ["title", "feed_url"]


class HTMLPluginAdmin(admin.ModelAdmin):
    search_fields = ["title"]
    list_display_links = ["title"]
    list_display = ["title", "course_instance_id", "container_type", "views"]

    def course_instance_id(self, obj):
        return obj.container_pk


class ExternalIFramePluginAdmin(admin.ModelAdmin):
    search_fields = ["title", "service_url"]


admin.site.register(BaseTab, BaseTabAdmin)
admin.site.register(HTMLTab, HTMLTabAdmin)
admin.site.register(ExternalEmbeddedTab, ExternalEmbeddedTabAdmin)
admin.site.register(ExternalIFrameTab, ExternalIFrameTabAdmin)
admin.site.register(BasePlugin, BasePluginAdmin)
admin.site.register(RSSPlugin, RSSPluginAdmin)
admin.site.register(HTMLPlugin, HTMLPluginAdmin)
admin.site.register(ExternalIFramePlugin, ExternalIFramePluginAdmin)
