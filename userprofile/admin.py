from django.contrib import admin

from .models import UserProfile


class UserProfileAdmin(admin.ModelAdmin):
    search_fields = ("user__first_name", "user__last_name", "user__username", "student_id")


admin.site.register(UserProfile, UserProfileAdmin)
