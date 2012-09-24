from django.contrib import admin
from models import BaseTab, BasePlugin, RSSPlugin


class RSSPluginAdmin(admin.ModelAdmin):
    pass


admin.site.register(RSSPlugin, RSSPluginAdmin)
