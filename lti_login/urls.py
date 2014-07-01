from django.conf.urls.defaults import patterns
from lti_login.views import lti_login

urlpatterns = patterns('',
    (r'^(\d+)$', lti_login),
)
