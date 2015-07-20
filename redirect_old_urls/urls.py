from django.conf.urls import patterns, url


urlpatterns = patterns('redirect_old_urls.views',
    url(r'^course/(?P<course_url>[\w\d\-\.]+)/$', 'course'),
    url(r'^course/(?P<course_url>[\w\d\-\.]+)/(?P<instance_url>[\w\d\-\.]+)/$', 'instance'),
    url(r'^exercise/(?P<exercise_id>\d+)/$', 'exercise'),
)
