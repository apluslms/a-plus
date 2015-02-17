from django.conf.urls.defaults import *
from userprofile.views import view_groups

urlpatterns = patterns('',
    (r'groups/$', view_groups),
)
