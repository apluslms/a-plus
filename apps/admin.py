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

class HTMLPluginAdmin(admin.ModelAdmin):
    list_display_links = ["title"]
    list_display = ["title", "course_instance_id", "container_type", "views"]

    def course_instance_id(self, obj):
        return obj.container_pk

admin.site.register(BaseTab)
admin.site.register(HTMLTab)
admin.site.register(ExternalEmbeddedTab)
admin.site.register(ExternalIFrameTab)
admin.site.register(BasePlugin)
admin.site.register(RSSPlugin)
admin.site.register(HTMLPlugin, HTMLPluginAdmin)
admin.site.register(ExternalIFramePlugin)
