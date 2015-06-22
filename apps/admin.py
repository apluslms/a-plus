from django.contrib import admin

from .models import ExternalIFrameTab, ExternalEmbeddedTab, RSSPlugin, \
    ExternalIFramePlugin


class ExternalIFrameTabAdmin(admin.ModelAdmin):
    pass
admin.site.register(ExternalIFrameTab, ExternalIFrameTabAdmin)


class ExternalEmbeddedTabAdmin(admin.ModelAdmin):
    pass
admin.site.register(ExternalEmbeddedTab, ExternalEmbeddedTabAdmin)


class RSSPluginAdmin(admin.ModelAdmin):
    pass
admin.site.register(RSSPlugin, RSSPluginAdmin)


class ExternalIFramePluginAdmin(admin.ModelAdmin):
    pass
admin.site.register(ExternalIFramePlugin, ExternalIFramePluginAdmin)
