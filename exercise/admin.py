# Django
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

# A+
from exercise.exercise_models import *
from exercise.submission_models import *


class CourseModuleAdmin(admin.ModelAdmin):
    list_display_links = ("name",)
    list_display = ("name", "course_instance", "opening_time", "closing_time")
    list_filter = ["course_instance", "opening_time", "closing_time"]

def real_class(obj):
    """ Returns the leaf class name of an exercise. """
    return obj.as_leaf_class().__class__.__name__
real_class.short_description = _('Real class')


class LearningObjectCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "course_instance"]
    list_filter = ["course_instance"]

    # TODO: Django 1.3 only considers the first item of this list. Fixed in 1.4.
    """https://docs.djangoproject.com/en/1.3/ref/contrib/admin/#django.contrib.a
    dmin.ModelAdmin.ordering"""
    ordering = ["course_instance", "order", "id"]


class BaseExerciseAdmin(admin.ModelAdmin):
    list_display_links = ["name"]
    list_display = ["name", "course_module", "max_points", real_class]
    list_filter = ["course_module__course_instance", "course_module"]
    
    class Media:
        js = ('/static/tiny_mce/tiny_mce.js',
              '/static/js/tiny_mce_textareas.js',)


class AsynchronousExerciseAdmin(admin.ModelAdmin):
    pass

class SynchronousExerciseAdmin(admin.ModelAdmin):
    pass

class StaticExerciseAdmin(admin.ModelAdmin):
    pass


admin.site.register(CourseModule, CourseModuleAdmin)
admin.site.register(LearningObjectCategory, LearningObjectCategoryAdmin)
admin.site.register(BaseExercise, BaseExerciseAdmin)
admin.site.register(AsynchronousExercise, AsynchronousExerciseAdmin)
admin.site.register(SynchronousExercise, SynchronousExerciseAdmin)
admin.site.register(StaticExercise, StaticExerciseAdmin)

def course_wrapper(obj):
    return obj.get_course_instance()
course_wrapper.short_description = _('Course instance')

def submitter_wrapper(obj):
    return ", ".join([profile.get_shortname() for profile in obj.submitters.all()])
submitter_wrapper.short_description = _('Submitters')

class SubmissionAdmin(admin.ModelAdmin):
    list_display_links = ("id",)
    list_display = ("id", "exercise", course_wrapper, submitter_wrapper, "status", "grade", "submission_time")
    list_filter = ["exercise", "status", "grade", "submission_time", "exercise__course_module__course_instance", "exercise__course_module", "submitters__user__username"]

class SubmittedFileAdmin(admin.ModelAdmin):
    pass

admin.site.register(Submission, SubmissionAdmin)
admin.site.register(SubmittedFile, SubmittedFileAdmin)
