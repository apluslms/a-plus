from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from course.models import Course, CourseInstance, CourseHook
from userprofile.models import UserProfile


def instance_url(instance):
    """
    Returns the URL for the admin listing.
    """
    return instance.get_absolute_url()

instance_url.short_description = _('URL')


class CourseAdmin(admin.ModelAdmin):
    
    list_display_links = ["id"]
    list_display = ["id", "name", "code"]
    list_editable = ["name", "code"]
    filter_horizontal = ["teachers"]

    def get_queryset(self, request):
        if not request.user.is_superuser:
            profile = UserProfile.get_by_request(request)
            return profile.teaching_courses
        else:
            return self.model.objects.filter()


class CourseInstanceAdmin(admin.ModelAdmin):
    
    list_display_links = ["instance_name"]
    list_display = ["course", "instance_name", "starting_time", "ending_time", instance_url]
    list_filter = ["course", "starting_time", "ending_time"]
    filter_horizontal = ["assistants"]

    def get_queryset(self, request):
        if not request.user.is_superuser:
            profile = UserProfile.get_by_request(request)
            return self.model.objects.where_staff_includes(profile)
        else:
            return self.model.objects.all()


admin.site.register(Course, CourseAdmin)
admin.site.register(CourseInstance, CourseInstanceAdmin)
admin.site.register(CourseHook)
