from django.contrib import admin

from deviations.models import DeadlineRuleDeviation, MaxSubmissionsRuleDeviation


class DeadlineRuleDeviationAdmin(admin.ModelAdmin):
    search_fields = ["submitter__student_id", "submitter__user__username",
        "submitter__user__first_name", "submitter__user__last_name",
        "submitter__user__email", "exercise__name"]
    list_display = ["submitter", "exercise", "extra_minutes", ]
    list_filter = ["exercise__course_module__course_instance"]
    raw_id_fields = ["submitter",]


class MaxSubmissionsRuleDeviationAdmin(admin.ModelAdmin):
    search_fields = ["submitter__student_id", "submitter__user__username",
        "submitter__user__first_name", "submitter__user__last_name",
        "submitter__user__email", "exercise__name"]
    raw_id_fields = ["submitter",]


admin.site.register(DeadlineRuleDeviation, DeadlineRuleDeviationAdmin)
admin.site.register(MaxSubmissionsRuleDeviation, MaxSubmissionsRuleDeviationAdmin)
