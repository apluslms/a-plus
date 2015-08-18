from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'^login/$', views.login, name="shibboleth-login"),
    url(r'^debug/$', views.debug),
]
