from django.contrib import admin

from .models import CourseDiplomaDesign, StudentDiploma


class CourseDiplomaDesignAdmin(admin.ModelAdmin):
    raw_id_fields = ('exercises_to_pass', 'modules_to_pass')

admin.site.register(CourseDiplomaDesign, CourseDiplomaDesignAdmin)
admin.site.register(StudentDiploma)
