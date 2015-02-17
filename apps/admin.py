from django.contrib import admin
from models import ExternalIFrameTab, EmbeddedTab, RSSPlugin,\
    ExternalIFramePlugin


class ExternalIFrameTabAdmin(admin.ModelAdmin):
    pass
admin.site.register(ExternalIFrameTab, ExternalIFrameTabAdmin)


class EmbeddedTabAdmin(admin.ModelAdmin):
    pass
admin.site.register(EmbeddedTab, EmbeddedTabAdmin)


class RSSPluginAdmin(admin.ModelAdmin):
    pass
admin.site.register(RSSPlugin, RSSPluginAdmin)


class ExternalIFramePluginAdmin(admin.ModelAdmin):
    pass
admin.site.register(ExternalIFramePlugin, ExternalIFramePluginAdmin)