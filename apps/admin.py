from django.contrib import admin
from models import *


class RSSPluginAdmin(admin.ModelAdmin):
    pass
admin.site.register(RSSPlugin, RSSPluginAdmin)


class IFrameToServicePluginAdmin(admin.ModelAdmin):
    pass
admin.site.register(IFrameToServicePlugin, IFrameToServicePluginAdmin)

