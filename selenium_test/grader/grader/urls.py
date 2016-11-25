from django.conf.urls import patterns, include, url
from django.contrib import admin

from exercises import views

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'grader.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^first_exercise/$', views.first),
    url(r'^file_exercise/$', views.file),
    url(r'^ajax_exercise/$', views.ajax, name="ajax"),
)
