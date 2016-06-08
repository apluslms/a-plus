from django.conf.urls import url, include
from rest_framework.routers import DefaultRouter

import userprofile.api.views
import exercise.api.views
import course.api.views

api_router = DefaultRouter()
api_router.register(r'users', userprofile.api.views.UserViewSet, base_name='user')
api_router.register(r'learningobjects', exercise.api.views.LearningObjectViewSet, base_name='learningobject')
api_router.register(r'courses', course.api.views.CourseViewSet, base_name='course')
# Submissions are categorized by exercises for example:
# api/v2/exercises/hello_world/submissions/1
api_router.register(r'exercises/', exercise.api.views.SubmissionViewSet, base_name='submission')

urlpatterns = [
    url(r'^', include(api_router.urls, namespace='api')),

    # For login/logout etc. pages in Django REST Framework
    url(r'^api-auth/', include('rest_framework.urls',
                               namespace='rest_framework')),
]
