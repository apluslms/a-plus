from django.contrib import admin
from external_services.models import LTIService, LinkService, MenuItem


class LinkServiceAdmin(admin.ModelAdmin):
    list_display_links = ["id"]

    list_display = ["id",
                    "menu_label",
                    "url",
                    "enabled",
                    "content_type",]

    readonly_fields = ("content_type",)

class LTIServiceAdmin(admin.ModelAdmin):
    list_display_links = ["id"]

    list_display = ["id",
                    "menu_label",
                    "url"]

class MenuItemAdmin(admin.ModelAdmin):
	list_display_links = ["id"]

	list_display = ["id",
					"service",
					"course_instance",
					"enabled",]

admin.site.register(LTIService, LTIServiceAdmin)
admin.site.register(LinkService, LinkServiceAdmin)
admin.site.register(MenuItem, MenuItemAdmin)
