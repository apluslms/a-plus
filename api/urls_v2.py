from django.conf import settings
from django.conf.urls import url, include
from rest_framework_extensions.routers import ExtendedDefaultRouter

import userprofile.api.views
import course.api.views
import exercise.api.views
import exercise.api.csv.views
import external_services.api.views


api = ExtendedDefaultRouter()

api.register(r'users',
             userprofile.api.views.UserViewSet,
             basename='user')

with api.register(r'courses',
                  course.api.views.CourseViewSet,
                  basename='course') as courses:
    courses.register(r'exercises',
                     course.api.views.CourseExercisesViewSet,
                     basename='course-exercises')
    courses.register(r'students',
                     course.api.views.CourseStudentsViewSet,
                     basename='course-students')
    courses.register(r'usertags',
                     course.api.views.CourseUsertagsViewSet,
                     basename='course-usertags')
    courses.register(r'taggings',
                     course.api.views.CourseUsertaggingsViewSet,
                     basename='course-taggings')
    courses.register(r'points',
                     exercise.api.views.CoursePointsViewSet,
                     basename='course-points')
    courses.register(r'submissiondata',
                     exercise.api.csv.views.CourseSubmissionDataViewSet,
                     basename='course-submissiondata')
    courses.register(r'aggregatedata',
                     exercise.api.csv.views.CourseAggregateDataViewSet,
                     basename='course-aggregatedata')

with api.register(r'exercises',
                  exercise.api.views.ExerciseViewSet,
                  basename='exercise') as exercises:
    exercises.register(r'submissions',
                       exercise.api.views.ExerciseSubmissionsViewSet,
                       basename='exercise-submissions'),
    exercises.register(r'submitter_stats',
                       exercise.api.views.ExerciseSubmitterStatsViewSet,
                       basename='exercise-submitter_stats')

with api.register(r'submissions',
                  exercise.api.views.SubmissionViewSet,
                  basename='submission') as submissions:
    submissions.register(r'files',
                         exercise.api.views.SubmissionFileViewSet,
                         basename='submission-files'),

urlpatterns = [
    url(r'^', include((api.urls, 'api'), namespace='api')),

    url(r'^me', userprofile.api.views.MeDetail.as_view()),
    url(r'^lti-outcomes', external_services.api.views.LTIExerciseBasicOutcomesView.as_view(), name='lti-outcomes'),
]


if getattr(settings, 'API_DEBUG', False):
    # Print list of api urls
    _urls = [(url.callback.cls.__name__, url.name or '-', url.pattern) for url in api.urls if url.callback]
    _urls += [(url.callback.cls.__name__, url.name or '-', url.pattern) for url in urlpatterns if url.callback]
    _lens = {'v': max(len(v) for v, n, p in _urls), 'n': max(len(url.name) for url in api.urls)}
    _urls = ("  - {:<{v:d}s} {:<{n:d}s} {!s:s}".format(*a, **_lens) for a in _urls)
    print(" API URLS:", *_urls, sep='\n')

    # Print list of api view permissions
    _vseen = set()
    _views = [url.callback.cls for url in api.urls if url.callback]
    _views += [url.callback.cls for url in urlpatterns if url.callback]
    _methods = ('list', 'create', 'retrieve', 'update', 'partial_update', 'destroy')
    _get_methods = lambda v: ' '.join(((m[0].upper() if hasattr(v, m) else ' ') for m in _methods))
    _get_perms = lambda v: ', '.join(p.__class__.__name__ for p in v().get_permissions())
    _views = [(v.__name__, _get_methods(v), _get_perms(v)) for v in _views if not (v in _vseen or _vseen.add(v))]
    _lens['m'] = max(len(m) for v, m, p in _views)
    _perms = ("  - {:<{v:d}s} {:<{m:d}s} {:s}".format(*a, **_lens) for a in _views)
    print(" API PERMS:", *_perms, sep='\n')
    print(" API methods:", ', '.join(m.capitalize() for m in _methods))

    # clean vars out of memory
    del _urls, _lens, _vseen, _views, _methods, _get_methods, _get_perms, _perms
