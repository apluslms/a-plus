from django.contrib import admin
from .models import ExamSession, ExamAttempt

# Register your models here.


class ExamSessionAdmin(admin.ModelAdmin):
    pass


admin.site.register(ExamSession, ExamSessionAdmin)
admin.site.register(ExamAttempt)
