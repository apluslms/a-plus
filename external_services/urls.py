from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'^lti/(\d+)/$', views.lti_login, name="lti-login"),
]
