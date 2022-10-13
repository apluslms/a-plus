from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from course.models import (
    Course,
    CourseInstance,
    Enrollment,
    StudentGroup,
    CourseHook,
    CourseModule,
    LearningObjectCategory,
    UserTag,
    UserTagging,
)
from lib.admin_helpers import RecentCourseInstanceListFilter


def instance_url(instance):
    """
    Returns the URL for the admin listing.
    """
    return instance.get_absolute_url()


instance_url.short_description = _('URL')


class CourseAdmin(admin.ModelAdmin):
    search_fields = (
        'name',
        'code',
        'url',
    )
    list_display_links = (
        'id',
        'name',
    )
    list_display = (
        'id',
        'name',
        'code',
        'url',
    )


class CourseInstanceAdmin(admin.ModelAdmin):
    search_fields = (
        'instance_name',
        'course__name',
        'course__code',
    )
    list_display_links = ('instance_name',)
    list_display = (
        'course',
        'instance_name',
        'visible_to_students',
        'starting_time',
        'ending_time',
        instance_url,
    )
    list_filter = (
        'course',
        'visible_to_students',
        'starting_time',
        'ending_time',
    )
    raw_id_fields = ('course',)

    def get_queryset(self, request):
        if request.user.is_superuser:
            return super().get_queryset(request)
        return CourseInstance.objects.get_teaching(request.user.userprofile)


class EnrollmentAdmin(admin.ModelAdmin):
    search_fields = (
        'course_instance__instance_name',
        'course_instance__course__name',
        'course_instance__course__code',
        'user_profile__student_id',
        'user_profile__user__username',
        'user_profile__user__first_name',
        'user_profile__user__last_name',
        'user_profile__user__email',
    )
    list_display_links = ('user_profile',)
    list_display = (
        'course_instance',
        'user_profile',
        'role',
        'status',
        'timestamp',
    )
    list_filter = (
        RecentCourseInstanceListFilter,
    )
    raw_id_fields = (
        'course_instance',
        'selected_group',
        'user_profile',
    )
    readonly_fields = ('timestamp',)


class CourseModuleAdmin(admin.ModelAdmin):
    search_fields = (
        'name',
        'course_instance__instance_name',
        'course_instance__course__name',
        'course_instance__course__code',
    )
    list_display_links = ('__str__',)
    list_display = ('course_instance',
        '__str__',
        'opening_time',
        'reading_opening_time',
        'closing_time',
        instance_url,
    )
    list_filter = (
        RecentCourseInstanceListFilter,
        'opening_time',
        'closing_time',
    )
    raw_id_fields = ('course_instance',)


class LearningObjectCategoryAdmin(admin.ModelAdmin):
    search_fields = (
        'name',
        'course_instance__instance_name',
        'course_instance__course__name',
        'course_instance__course__code',
    )
    list_display_links = ('name',)
    list_display = (
        'course_instance',
        'name',
    )
    list_filter = (
        RecentCourseInstanceListFilter,
    )
    ordering = (
        'course_instance',
        'id',
    )
    raw_id_fields = ('course_instance',)


class StudentGroupAdmin(admin.ModelAdmin):
    search_fields = (
        'course_instance__instance_name',
        'course_instance__course__name',
        'course_instance__course__code',
        'members__student_id',
        'members__user__username',
        'members__user__first_name',
        'members__user__last_name',
        'members__user__email',
    )
    list_display = (
        'course_instance',
        'members_string',
        'timestamp',
    )
    list_display_links = ('members_string',)
    list_filter = (
        RecentCourseInstanceListFilter,
    )
    raw_id_fields = (
        'course_instance',
        'members',
    )
    readonly_fields = ('timestamp',)

    @admin.display(description=_('LABEL_MEMBERS'))
    def members_string(self, obj):
        return ", ".join(
            str(p) for p in obj.members.all()
        )


class UserTagAdmin(admin.ModelAdmin):
    search_fields = (
        'name',
        'course_instance__instance_name',
        'course_instance__course__name',
        'course_instance__course__code'
    )
    list_display = (
        'course_instance',
        'name',
        'slug',
        'visible_to_students',
    )
    list_display_links = (
        'name',
        'slug',
    )
    list_filter = (
        RecentCourseInstanceListFilter,
    )
    raw_id_fields = (
        'course_instance',
    )


class UserTaggingAdmin(admin.ModelAdmin):
    search_fields = (
        'tag__name',
        'course_instance__instance_name',
        'course_instance__course__name',
        'course_instance__course__code',
        'user__student_id',
        'user__user__username',
        'user__user__first_name',
        'user__user__last_name',
        'user__user__email',
    )
    list_display = (
        'course_instance',
        'tag',
        'user',
    )
    list_display_links = (
        'tag',
        'user',
    )
    list_filter = (
        RecentCourseInstanceListFilter,
    )
    raw_id_fields = (
        'course_instance',
        'tag',
        'user',
    )


class CourseHookAdmin(admin.ModelAdmin):
    search_fields = (
        'hook_url',
        'course_instance__instance_name',
        'course_instance__course__name',
        'course_instance__course__code',
    )
    raw_id_fields = ('course_instance',)


admin.site.register(Course, CourseAdmin)
admin.site.register(CourseInstance, CourseInstanceAdmin)
admin.site.register(Enrollment, EnrollmentAdmin)
admin.site.register(StudentGroup, StudentGroupAdmin)
admin.site.register(CourseHook, CourseHookAdmin)
admin.site.register(CourseModule, CourseModuleAdmin)
admin.site.register(LearningObjectCategory, LearningObjectCategoryAdmin)
admin.site.register(UserTag, UserTagAdmin)
admin.site.register(UserTagging, UserTaggingAdmin)
