from django.contrib import admin

from .models import CourseDiplomaDesign, StudentDiploma


class CourseDiplomaDesignAdmin(admin.ModelAdmin):
    search_fields = (
        'course__instance_name',
        'course__course__code',
        'course__course__name',
        'title',
    )
    list_display = (
        'course',
        'availability',
        'title',
        'date',
    )
    list_display_links = (
        'course',
        'title',
    )
    list_filter = (
        ('course', admin.RelatedOnlyFieldListFilter),
    )
    raw_id_fields = (
        'course',
        'exercises_to_pass',
        'modules_to_pass',
    )


class StudentDiplomaAdmin(admin.ModelAdmin):
    search_fields = (
        'name',
        'profile__student_id',
        'profile__user__username',
        'profile__user__first_name',
        'profile__user__last_name',
        'profile__user__email',
        'design__course__instance_name',
        'design__course__course__code',
        'design__course__course__name',
    )
    list_display = (
        'design',
        'profile',
        'created',
        'grade',
    )
    list_display_links = (
        'profile',
    )
    list_filter = (
        ('design__course', admin.RelatedOnlyFieldListFilter),
    )
    raw_id_fields = (
        'design',
        'profile',
    )
    readonly_fields = ('created',)


admin.site.register(CourseDiplomaDesign, CourseDiplomaDesignAdmin)
admin.site.register(StudentDiploma, StudentDiplomaAdmin)
