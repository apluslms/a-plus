from django.contrib import admin
from .models import UserProfile, StudentGroup

class UserProfileAdmin(admin.ModelAdmin):
    pass

class StudentGroupAdmin(admin.ModelAdmin):
    pass

admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(StudentGroup, StudentGroupAdmin)
