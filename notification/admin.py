from django.contrib import admin

from notification.models import Notification

class NotificationAdmin(admin.ModelAdmin):
     search_fields = ("subject", "notification", "sender__user__first_name", 
     "recipient__user__first_name", "course_instance__course__name")
     autocomplete_fields = ("sender", "recipient", "course_instance")


admin.site.register(Notification, NotificationAdmin)
