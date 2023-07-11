from django.conf import settings
from django.urls import re_path

from . import views


urlpatterns = [
    re_path(r'^shibboleth/login/$', views.login, name="shibboleth-login"),
    re_path(r'^Shibboleth.sso/haka_login$', views.login, name="haka-login"),
]

if settings.DEBUG:
    urlpatterns.append(re_path(r'^debug/$', views.debug))
