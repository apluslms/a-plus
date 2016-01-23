from django.conf.urls import patterns, include, url
from django.conf.global_settings import DEBUG

urlpatterns = patterns('',
    url(r'^gitmanager/', include('manager.urls')),
    url(r'^', include('access.urls')),
)

# Allow debugging while mapped to /grader.
if DEBUG:
    urlpatterns = patterns('',
        url(r'^(grader/)?gitmanager/', include('manager.urls')),
        url(r'^(grader/)?', include('access.urls')),
    )
