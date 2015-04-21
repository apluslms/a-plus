from django.conf.urls import patterns
from .views import lti_login

urlpatterns = patterns('',
    (r'^lti/(\d+)$', lti_login),
)
