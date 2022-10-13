from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from rest_framework.authtoken.admin import TokenAdmin

from .models import UserProfile


class UserProfileAdmin(admin.ModelAdmin):
    search_fields = (
        'user__first_name',
        'user__last_name',
        'user__username',
        'user__email',
        'student_id',
        'organization',
    )
    list_display = (
        'id',
        'get_user',
        'student_id',
        'organization',
    )
    list_display_links = (
        'id',
        'get_user',
        'student_id',
    )
    raw_id_fields = ('user',)

    @admin.display(description=_('LABEL_USER'))
    def get_user(self, obj):
        return f'{obj.user.get_username()} | user_id={obj.user.pk} | {obj.user.get_full_name()} | {obj.user.email}'


admin.site.register(UserProfile, UserProfileAdmin)

# Don't display a dropdown for selecting a user on the Token admin page.
TokenAdmin.raw_id_fields = ('user',)
TokenAdmin.search_fields = (
    'user__first_name',
    'user__last_name',
    'user__username',
    'user__userprofile__student_id',
)
