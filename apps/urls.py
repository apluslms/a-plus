from django.conf.urls import patterns
from apps.views import view_tab

urlpatterns = patterns('',
    (r'tab/(?P<tab_id>\d+)/$', view_tab),
)
