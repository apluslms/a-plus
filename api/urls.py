from userprofile import userprofile_api
from exercise import exercise_api
from django.conf.urls import url, patterns, include

# REST Framework URLs. The root of API, e.g. www.plus.cs.tut.fi/api
# To get deeper, take a look at folders: exercise, userprofile
urlpatterns = patterns('',
    # api/userprofile: lists all userprofiles.
    # GET is available for everyone
    # POST is for admin
    url(r'^userprofile/$', userprofile_api.UserList.as_view()),

    # e.g. api/userprofile/1: GET/PUT/PATCH/DELETE to single user
    # GET is for everyone and others need to be authenticated
    url(r'^userprofile/(?P<pk>[0-9]+)/$', userprofile_api.UserDetail.as_view()),

    # api/learningobject: GET list of exercises
    url(r'^learningobject/$', exercise_api.LearningObjectList.as_view()),

    # api/submission: GET/POST a submission
    # GET is for getting the result of SubmissionDetail
    # POST is for making new SubmissionDetail
    url(r'^submission/$', exercise_api.SubmissionList.as_view()),
)

# For login/logout etc. pages in REST Framework
urlpatterns += [
    url(r'^api-auth/', include('rest_framework.urls',
                               namespace='rest_framework')),
]
