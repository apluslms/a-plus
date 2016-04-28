from django.conf.urls import url, patterns, include

from userprofile.api.views import *
from exercise.api.views import *


urlpatterns = patterns('',
    url(r'^userprofile/$', UserList.as_view()),
    url(r'^userprofile/(?P<pk>[0-9]+)/$', UserDetail.as_view()),
    url(r'^learningobject/$', LearningObjectList.as_view()),
    url(r'^submission/$', SubmissionList.as_view()),

    # For login/logout etc. pages in Django REST Framework
    url(r'^api-auth/', include('rest_framework.urls',
                               namespace='rest_framework')),
)
