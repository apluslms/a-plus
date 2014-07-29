from django.contrib import admin
from lti_login.models import LTIService, LTIMenuItem

admin.site.register(LTIService)
admin.site.register(LTIMenuItem)
