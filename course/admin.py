from django.contrib import admin
from course.models import Course, CourseInstance, CourseHook


class CourseAdmin(admin.ModelAdmin):
    list_display_links = ["id"]

    list_display = ["id",
                           "name",
                           "code"]

    list_editable = ["name",
                           "code"]

    filter_horizontal = ["teachers"]

    def get_queryset(self, request):
        if not request.user.is_superuser:
            return request.user.userprofile.teaching_courses
        else:
            return self.model.objects.filter()


def instance_url(obj):
    """ This method returns the URL to the given object. This method is used as
        a callable that is included in the admin views. """

    return obj.get_absolute_url()

# This gives the instance_url admin column the title "Url"
instance_url.short_description = 'Url'


class CourseInstanceAdmin(admin.ModelAdmin):
    list_display_links = ["instance_name"]

    list_display = ["course",
                    "instance_name",
                    "starting_time",
                    "ending_time",
                    instance_url]

    list_filter = ["course",
                   "starting_time",
                   "ending_time"]

    filter_horizontal = ["assistants"]

    def get_queryset(self, request):
        if not request.user.is_superuser:
            return self.model.objects.where_staff_includes(request.user.userprofile)
        else:
            return self.model.objects.all()

admin.site.register(Course, CourseAdmin)
admin.site.register(CourseInstance, CourseInstanceAdmin)
admin.site.register(CourseHook)
