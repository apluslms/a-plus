from django.conf.urls import include, url
from django.contrib import admin

from exercises import views

urlpatterns = [
    url(r'^first_exercise/$', views.first),
    url(r'^file_exercise/$', views.file),
    url(r'^ajax_exercise/$', views.ajax, name="ajax"),
]
