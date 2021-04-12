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
from userprofile.models import UserProfile


def instance_url(instance):
    """
    Returns the URL for the admin listing.
    """
    return instance.get_absolute_url()

instance_url.short_description = _('URL')


class CourseAdmin(admin.ModelAdmin):

    search_fields = ["name", "code", "teachers__user__username",
        "teachers__user__first_name", "teachers__user__last_name",
        "teachers__user__email"]
    list_display_links = ["id"]
    list_display = ["id", "name", "code", "url"]
    #list_editable = ["name", "code"]
    filter_horizontal = ["teachers"]
    raw_id_fields = ["teachers",]

    def get_queryset(self, request):
        if not request.user.is_superuser:
            profile = UserProfile.get_by_request(request)
            return profile.teaching_courses
        else:
            return self.model.objects.filter()


class CourseInstanceAdmin(admin.ModelAdmin):

    search_fields = ("instance_name", "course__name", "course__code")
    list_display_links = ["instance_name"]
    list_display = ["course", "instance_name", "visible_to_students",
        "starting_time", "ending_time", instance_url]
    list_filter = ["course", "visible_to_students",
        "starting_time", "ending_time"]
    filter_horizontal = ["assistants"]
    raw_id_fields = ["assistants",]

    def get_queryset(self, request):
        if not request.user.is_superuser:
            profile = UserProfile.get_by_request(request)
            return self.model.objects.where_staff_includes(profile)
        else:
            return self.model.objects.all()


class EnrollmentAdmin(admin.ModelAdmin):
    search_fields = ["course_instance__instance_name",
        "course_instance__course__name", "course_instance__course__code",
        "user_profile__student_id", "user_profile__user__username",
        "user_profile__user__first_name", "user_profile__user__last_name",
        "user_profile__user__email"]
    list_display_links = ("user_profile",)
    list_display = ("course_instance", "user_profile", "timestamp")
    list_filter = ("course_instance",)
    raw_id_fields = ("user_profile",)
    readonly_fields = ("timestamp",)


class CourseModuleAdmin(admin.ModelAdmin):

    search_fields = ["name", "course_instance__instance_name",
        "course_instance__course__name", "course_instance__course__code"]
    list_display_links = ("__str__",)
    list_display = ("course_instance", "__str__", "opening_time",
        "reading_opening_time", "closing_time", instance_url)
    list_filter = ["course_instance", "opening_time", "closing_time"]


class LearningObjectCategoryAdmin(admin.ModelAdmin):

    search_fields = ["name", "course_instance__instance_name",
        "course_instance__course__name", "course_instance__course__code"]
    list_display_links = ("name",)
    list_display = ("course_instance", "name")
    list_filter = ("course_instance",)
    ordering = ["course_instance", "id"]


class StudentGroupAdmin(admin.ModelAdmin):

    search_fields = ["course_instance__instance_name",
        "course_instance__course__name", "course_instance__course__code",
        "members__student_id", "members__user__username",
        "members__user__first_name", "members__user__last_name",
        "members__user__email"]
    raw_id_fields = ("members",)


class UserTagAdmin(admin.ModelAdmin):

    search_fields = ["name", "course_instance__instance_name",
        "course_instance__course__name", "course_instance__course__code"]


class UserTaggingAdmin(admin.ModelAdmin):

    search_fields = ["tag__name", "course_instance__instance_name",
        "course_instance__course__name", "course_instance__course__code",
        "user__student_id", "user__user__username", "user__user__first_name",
        "user__user__last_name", "user__user__email"]
    raw_id_fields = ("user",)


class CourseHookAdmin(admin.ModelAdmin):
    search_fields = ["hook_url", "course_instance__instance_name",
        "course_instance__course__name", "course_instance__course__code"]


admin.site.register(Course, CourseAdmin)
admin.site.register(CourseInstance, CourseInstanceAdmin)
admin.site.register(Enrollment, EnrollmentAdmin)
admin.site.register(StudentGroup, StudentGroupAdmin)
admin.site.register(CourseHook, CourseHookAdmin)
admin.site.register(CourseModule, CourseModuleAdmin)
admin.site.register(LearningObjectCategory, LearningObjectCategoryAdmin)
admin.site.register(UserTag, UserTagAdmin)
admin.site.register(UserTagging, UserTaggingAdmin)
