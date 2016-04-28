from userprofile import userprofile_api
from exercise import exercise_api
from django.conf.urls import url, patterns, include

# REST Framework URLs
urlpatterns = patterns('',
    url(r'^userprofile/$', userprofile_api.UserList.as_view()),
    url(r'^userprofile/(?P<pk>[0-9]+)/$', userprofile_api.UserDetail.as_view()),

    url(r'^learningobject/$', exercise_api.LearningObjectList.as_view()),
    url(r'^submission/$', exercise_api.SubmissionList.as_view()),
)

# For login/logout etc. pages in REST Framework
urlpatterns += [
    url(r'^api-auth/', include('rest_framework.urls',
                               namespace='rest_framework')),
]
