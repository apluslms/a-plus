from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'^course/(?P<course_url>[\w\d\-\.]+)/$',
        views.course),
    url(r'^course/(?P<course_url>[\w\d\-\.]+)/(?P<instance_url>[\w\d\-\.]+)/$',
        views.instance),
    url(r'^exercise/(?P<exercise_id>\d+)/$',
        views.exercise),
    url(r'^(?P<course_url>[\w\d\-\.]+)/(?P<instance_url>[\w\d\-\.]+)/exercises/(?P<exercise_id>\d+)/$',
        views.instance_exercise),
]
