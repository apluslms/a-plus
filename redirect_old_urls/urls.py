from django.urls import re_path

from . import views


urlpatterns = [
    re_path(r'^course/(?P<course_url>[\w\d\-\.]+)/$',
        views.course),
    re_path(r'^course/(?P<course_url>[\w\d\-\.]+)/(?P<instance_url>[\w\d\-\.]+)/$',
        views.instance),
    re_path(r'^exercise/(?P<exercise_id>\d+)/$',
        views.exercise),
    re_path(r'^(?P<course_url>[\w\d\-\.]+)/(?P<instance_url>[\w\d\-\.]+)/exercises/(?P<exercise_id>\d+)/$',
        views.instance_exercise),
]
