from django.contrib import admin

from .models import UserProfile


class UserProfileAdmin(admin.ModelAdmin):
    search_fields = ("user__first_name", "user__last_name", "user__username", "student_id")
    raw_id_fields = ("user",)


admin.site.register(UserProfile, UserProfileAdmin)

# Don't display a dropdown for selecting a user on the Token admin page.
from rest_framework.authtoken.admin import TokenAdmin
TokenAdmin.raw_id_fields = ["user"]
