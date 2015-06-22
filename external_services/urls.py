from django.conf.urls import patterns, url


urlpatterns = patterns('external_services.views',
    url(r'^lti/(\d+)$', 'lti_login'),
)
