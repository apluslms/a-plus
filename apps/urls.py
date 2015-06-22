from django.conf.urls import patterns, url


urlpatterns = patterns('apps.views',
    url(r'tab/(?P<tab_id>\d+)/$', 'view_tab'),
)
