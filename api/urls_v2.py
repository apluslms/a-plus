from django.conf import settings
from django.conf.urls import url, include
from rest_framework_extensions.routers import ExtendedDefaultRouter

import userprofile.api.views, \
       course.api.views
from exercise.api.views import *

api = ExtendedDefaultRouter()

api.register(r'users',
             userprofile.api.views.UserViewSet,
             base_name='user')

with api.register(r'courses',
                  course.api.views.CourseViewSet,
                  base_name='course') as courses:
    courses.register(r'exercises',
                     course.api.views.CourseExercisesViewSet,
                     base_name='course-exercises')
    courses.register(r'students',
                     course.api.views.CourseStudentsViewSet,
                     base_name='course-students')

urlpatterns = [
    url(r'^', include(api.urls, namespace='api')),
    url(r'^learningobject/$', LearningObjectList.as_view()),
    url(r'^submission/$', SubmissionList.as_view()),

    # For login/logout etc. pages in Django REST Framework
    url(r'^api-auth/', include('rest_framework.urls',
                               namespace='rest_framework')),
]

if settings.DEBUG:
    print(" API URLS:")
    for url in api.urls:
        print("  - %r" % (url,))
