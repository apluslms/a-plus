from django.contrib import admin

from deviations.models import DeadlineRuleDeviation, MaxSubmissionsRuleDeviation


class DeadlineRuleDeviationAdmin(admin.ModelAdmin):
    list_display = ["submitter", "exercise", "extra_minutes", ]
    list_filter = ["exercise__course_module__course_instance"]

admin.site.register(DeadlineRuleDeviation, DeadlineRuleDeviationAdmin)
admin.site.register(MaxSubmissionsRuleDeviation)
