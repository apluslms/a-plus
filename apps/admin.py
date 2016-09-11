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


admin.site.register(BaseTab)
admin.site.register(HTMLTab)
admin.site.register(ExternalEmbeddedTab)
admin.site.register(ExternalIFrameTab)
admin.site.register(BasePlugin)
admin.site.register(RSSPlugin)
admin.site.register(HTMLPlugin)
admin.site.register(ExternalIFramePlugin)
