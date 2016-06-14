from django.conf.urls import url, include
from rest_framework.routers import DefaultRouter

import userprofile.api.views
import exercise.api.views
import course.api.views

api_router = DefaultRouter()
api_router.register(r'users', userprofile.api.views.UserViewSet, base_name='user')
api_router.register(r'learningobjects', exercise.api.views.LearningObjectViewSet, base_name='learningobject')
api_router.register(r'courseinstances', course.api.views.CourseInstanceViewSet, base_name='course')

# ------------------------------------------------------------------------------
# API for PyCharm plugin

# Url for GETting information about an exercise. (List of exercises can be fetched
# from /api/v2/courses/johoh/kk2016/api/v2/courses/{kurssi_instanssi_id}/exercices)
# /api/v2/exercises/{exercise_id}
# (/api/v2/exercises/ does not actually exist)
api_router.register(r'exercises', exercise.api.views.ExerciseViewSet,
                    base_name='exercise')

# Url for submitting (POST) an exercise and for getting (GET) result of automatic
# assessment
# /api/v2/submissions/{submissions_id}
api_router.register(r'submissions', exercise.api.views.SubmissionViewSet,
                    base_name='submission')

# Url for checking that student has given correct arguments for plugin and GETting
# student information such as student id, enrolled course,
# /api/v2/me
# This is added in urlpattern below.

# ------------------------------------------------------------------------------

urlpatterns = [
    url(r'^', include(api_router.urls, namespace='api')),

    url(r'^me', userprofile.api.views.MeDetail.as_view()),

    # For login/logout etc. pages in Django REST Framework
    url(r'^api-auth/', include('rest_framework.urls',
                               namespace='rest_framework')),
]
