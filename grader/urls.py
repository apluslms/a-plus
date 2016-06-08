from django.conf.urls import include, url
from django.conf.global_settings import DEBUG

import gitmanager.urls, access.urls

urlpatterns = [
    url(r'^gitmanager/', include(gitmanager.urls)),
    url(r'^', include(access.urls)),
]
