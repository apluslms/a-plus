# Django
from django.contrib import admin

# A+
from notification.models import Notification

class NotificationAdmin(admin.ModelAdmin):
    pass

admin.site.register(Notification, NotificationAdmin)

