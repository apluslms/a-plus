from django.contrib import admin
from models import *


class ExternalIFrameTabAdmin(admin.ModelAdmin):
    pass
admin.site.register(ExternalIFrameTab, ExternalIFrameTabAdmin)


class RSSPluginAdmin(admin.ModelAdmin):
    pass
admin.site.register(RSSPlugin, RSSPluginAdmin)


class IFrameToServicePluginAdmin(admin.ModelAdmin):
    pass
admin.site.register(IFrameToServicePlugin, IFrameToServicePluginAdmin)

