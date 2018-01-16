from django.conf import settings
from django.conf.urls import include, url
from django.conf.global_settings import DEBUG

import os

urlpatterns = []

if 'gitmanager' in settings.INSTALLED_APPS:
    import gitmanager.urls
    urlpatterns.append(url(r'^gitmanager/', include(gitmanager.urls)))

import access.urls
urlpatterns.append(url(r'^', include(access.urls)))

os.umask(0o002)
