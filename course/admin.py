from django.contrib import admin
from course.models import Course, CourseInstance, CourseHook
from django.db.models import Q

class CourseAdmin(admin.ModelAdmin):
    list_display_links  = ["id"]
    
    list_display        = ["id",
                           "name",
                           "code"]
    
    list_editable       = ["name",
                           "code"]

    filter_horizontal   = ["teachers"]
    
    def queryset(self, request):
        if not request.user.is_superuser:
            return request.user.get_profile().teaching_courses
        else:
            # TODO: test that the manager works
            # Previously: return self.model._default_manager.filter()
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
    
    def queryset(self, request):
        if not request.user.is_superuser:
            return request.user.get_profile().get_courseinstance_staff_queryset()
        else:
            # TODO: test that the manager works
            # Previously: return self.model._default_manager.filter()
            return self.model.objects.filter()

admin.site.register(Course, CourseAdmin)
admin.site.register(CourseInstance, CourseInstanceAdmin)
admin.site.register(CourseHook)
