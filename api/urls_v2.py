from django.conf import settings
from django.conf.urls import url, include
from rest_framework_extensions.routers import ExtendedDefaultRouter

import userprofile.api.views
import course.api.views
import exercise.api.views


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
    courses.register(r'points',
                     course.api.views.CoursePointsViewSet,
                     base_name='course-points')

with api.register(r'exercises',
                  exercise.api.views.ExerciseViewSet,
                  base_name='exercise') as exercises:
    exercises.register(r'submissions',
                       exercise.api.views.ExerciseSubmissionsViewSet,
                       base_name='exercise-submissions')
    exercises.register(r'submitter_stats',
                       exercise.api.views.ExerciseSubmitterStatsViewSet,
                       base_name='exervise-submitter_stats')

api.register(r'submissions',
             exercise.api.views.SubmissionViewSet,
             base_name='submission')

urlpatterns = [
    url(r'^', include(api.urls, namespace='api')),

    url(r'^me', userprofile.api.views.MeDetail.as_view()),
]

if settings.DEBUG:
    _len = max((len(url.name) for url in api.urls))
    _fmt = "  - %%-%ds %%s" % (_len,)
    _urls = '\n'.join((_fmt % (url.name, url.regex.pattern) for url in api.urls))
    print(" API URLS:\n%s" % (_urls,))
