from django.conf.urls.defaults import patterns
from external_services.views import lti_login

urlpatterns = patterns('',
    (r'^lti/(\d+)$', lti_login),
)
