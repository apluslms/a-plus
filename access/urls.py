from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^$', 'access.views.index'),
    url(r'^([\w-]+)/$', 'access.views.course'),
    url(r'^([\w-]+)/([\w-]+)$', 'access.views.exercise'),
    url(r'^pull-request$', 'access.views.pull_request'),
    url(r'^queue-length$', 'access.views.queue_length'),
    url(r'^null$', 'access.views.null'),
)
