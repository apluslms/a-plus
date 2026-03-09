from django.conf import settings
from django.urls import path

from . import views


urlpatterns = [
    path('shibboleth/login/', views.login, name="shibboleth-login"),
    path('Shibboleth.sso/haka_login', views.login, name="haka-login"),
]

if settings.DEBUG:
    urlpatterns.append(path('debug/', views.debug))
