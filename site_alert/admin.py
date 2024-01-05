from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from site_alert.models import SiteAlert


class SiteAlertAdmin(admin.ModelAdmin):
    search_fields = (
        'alert',
        'status',
    )
    list_display = (
        'id',
        'alert',
        'status',
    )


admin.site.register(SiteAlert, SiteAlertAdmin)
