from django.conf.urls import patterns
from userprofile.views import view_groups

urlpatterns = patterns('',
    (r'groups/$', view_groups),
)
