from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns('',
    url(r'^$', views.repos, name='manager-repos'),
    url(r'^new/$', views.edit, name='manager-edit'),
    url(r'^([\w-]+)/$', views.edit, name='manager-edit'),
    url(r'^([\w-]+)/updates$', views.updates, name='manager-updates'),
    url(r'^([\w-]+)/hook$', views.hook, name='manager-hook'),
)
