from django.conf.urls import url, include
from rest_framework.routers import DefaultRouter

import userprofile.api.views
from exercise.api.views import *

api_router = DefaultRouter()
api_router.register(r'users', userprofile.api.views.UserViewSet, base_name='user')

urlpatterns = [
    url(r'^', include(api_router.urls, namespace='api')),
    url(r'^learningobject/$', LearningObjectList.as_view()),
    url(r'^submission/$', SubmissionList.as_view()),

    # For login/logout etc. pages in Django REST Framework
    url(r'^api-auth/', include('rest_framework.urls',
                               namespace='rest_framework')),
]
