from django.urls import re_path

from exercises import views

urlpatterns = [
    re_path(r'^first_exercise/$', views.first),
    re_path(r'^file_exercise/$', views.file),
    re_path(r'^ajax_exercise/$', views.ajax, name="ajax"),
]
