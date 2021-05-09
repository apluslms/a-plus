from django.conf import settings
from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'^shibboleth/login/$', views.login, name="shibboleth-login"),
    url(r'^Shibboleth.sso/haka_login$', views.login, name="haka-login"),
]

if settings.DEBUG:
    urlpatterns.append(url(r'^debug/$', views.debug))
