from django.conf.urls.defaults import *
from apps.views import view_tab

urlpatterns = patterns('',
    (r'tab/(?P<tab_id>\d+)/$', view_tab),
)
