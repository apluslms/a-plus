from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^$', 'access.views.index'),
    url(r'^queue-length$', 'access.views.queue_length'),
    url(r'^test-result$', 'access.views.test_result'),
    url(r'^ajax-submit/([\w-]+)/([\w-]+)$', 'access.views.ajax_submit'),
    url(r'^([\w-]+)/$', 'access.views.course'),
    url(r'^([\w-]+)/aplus-json$', 'access.views.aplus_json'),
    url(r'^([\w-]+)/([\w-]+)$', 'access.views.exercise'),
)
