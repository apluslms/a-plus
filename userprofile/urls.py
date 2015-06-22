from django.conf.urls import patterns, url

from userprofile.views import view_groups


urlpatterns = patterns('',
    url(r'groups/$', view_groups),
)
