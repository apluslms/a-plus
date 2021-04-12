from django.contrib import admin

from .models import CourseDiplomaDesign, StudentDiploma


class CourseDiplomaDesignAdmin(admin.ModelAdmin):
    search_fields = ["course__instance__name"]
    raw_id_fields = ('exercises_to_pass', 'modules_to_pass')


class StudentDiplomaAdmin(admin.ModelAdmin):
    search_fields = ["name", "profile__student_id", "profile__user__username",
        "profile__user__first_name", "profile__user__last_name",
        "profile__user__email"]
    raw_id_fields = ('profile',)


admin.site.register(CourseDiplomaDesign, CourseDiplomaDesignAdmin)
admin.site.register(StudentDiploma, StudentDiplomaAdmin)
