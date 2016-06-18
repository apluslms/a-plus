from django.conf import settings
from django.conf.urls import url, include
from rest_framework_extensions.routers import ExtendedDefaultRouter

import userprofile.api.views, \
       course.api.views
from exercise.api.views import *
import exercise.api.views


api = ExtendedDefaultRouter()

api.register(r'users',
             userprofile.api.views.UserViewSet,
             base_name='user')

api.register(r'learningobjects',
                    exercise.api.views.LearningObjectViewSet,
                    base_name='learningobject')

# Url for GETting information about an exercise. (List of exercises can be fetched
# from /api/v2/courses/johoh/kk2016/api/v2/courses/{kurssi_instanssi_id}/exercices)
# /api/v2/exercises/{exercise_id}
# (/api/v2/exercises/ does not actually exist)
api.register(r'exercises',
                    exercise.api.views.ExerciseViewSet,
                    base_name='exercise')

# Url for submitting (POST) an exercise and for getting (GET) result of automatic
# assessment
# /api/v2/submissions/{submissions_id}
api.register(r'submissions',
                    exercise.api.views.SubmissionViewSet,
                    base_name='submission')

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

    # Url for checking that student has given correct arguments for plugin and
    # GETting student information such as student id, enrolled course, /api/v2/me
    url(r'^me', userprofile.api.views.MeDetail.as_view()),

    # For login/logout etc. pages in Django REST Framework
    url(r'^api-auth/', include('rest_framework.urls',
                               namespace='rest_framework')),
]

if settings.DEBUG:
    print(" API URLS:")
    for url in api.urls:
        print("  - %r" % (url,))
