from django.conf import settings
from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'^login/$', views.login, name="shibboleth-login"),
]

if settings.DEBUG:
    urlpatterns.append(url(r'^debug/$', views.debug))
