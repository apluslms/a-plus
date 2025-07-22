import copy

from django.conf import settings
from django.conf.urls import include
from django.urls import path, re_path
from rest_framework_extensions.routers import ExtendedDefaultRouter

import userprofile.api.views
import course.api.views
import course.api.lti_views
import exercise.api.views
import exercise.api.csv.views
import external_services.api.views
import authorization.api.views
import lib.api.statistics


class AplusRouter(ExtendedDefaultRouter):
    routes = copy.deepcopy(ExtendedDefaultRouter.routes)
    # Add DELETE to list routes. Enabled if there is method `destroy_many` in the viewset.
    # This could break if the super class definition in the framework is modified.
    # We have to assume that the first route in routes is the list route.
    # The framework does not map the DELETE method for it at all, so we do it here.
    routes[0].mapping['delete'] = 'destroy_many'

    def __init__(self):
        # The following causes URLs to be routed either with or without the trailing slash.
        # It is needed, because LTI 1.3 specifies some URLs that do not have trailing slash,
        # but Django (and A+) default behavior automatically assumes the trailing slash,
        # and some of the existing links to A+ material might assume this as well.
        # The side effect of this change is, that the reverse URLs for APIs now appear
        # without trailing slash, while before it was included in URL. Therefore the
        # comparisons in some of the API unit tests needed to be fixed, but calling the
        # API URLs in existing implementations should work without modifications, because
        # both URL variants are routed.
        super().__init__()
        self.trailing_slash = '/?'


api = AplusRouter()

api.register(r'users',
             userprofile.api.views.UserViewSet,
             basename='user')

with api.register(r'courses',
                  course.api.views.CourseViewSet,
                  basename='course') as courses:
    courses.register(r'exercises',
                     course.api.views.CourseExercisesViewSet,
                     basename='course-exercises')
    courses.register(r'tree',
                     course.api.views.CourseExerciseTreeViewSet,
                     basename='course-tree')
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
    courses.register(r'resultsdata',
                     exercise.api.csv.views.CourseResultsDataViewSet,
                     basename='course-resultsdata')
    courses.register(r'bestresultsdata',
                     exercise.api.csv.views.CourseBestResultsDataViewSet,
                     basename='course-resultsdata-best')
    courses.register(r'mygroups',
                     course.api.views.CourseOwnStudentGroupsViewSet,
                     basename='course-mygroups')
    courses.register(r'groups',
                     course.api.views.CourseStudentGroupsViewSet,
                     basename='course-groups')
    courses.register(r'news',
                     course.api.views.CourseNewsViewSet,
                     basename='course-news')
    courses.register(r'lineitems',
                    course.api.lti_views.CourseLineItemsViewSet,
                    basename='course-lineitems')

with api.register(r'exercises',
                  exercise.api.views.ExerciseViewSet,
                  basename='exercise') as exercises:
    exercises.register(r'submissions',
                       exercise.api.views.ExerciseSubmissionsViewSet,
                       basename='exercise-submissions')
    exercises.register(r'submitter_stats',
                       exercise.api.views.ExerciseSubmitterStatsViewSet,
                       basename='exercise-submitter_stats')

with api.register(r'submissions',
                  exercise.api.views.SubmissionViewSet,
                  basename='submission') as submissions:
    submissions.register(r'files',
                         exercise.api.views.SubmissionFileViewSet,
                         basename='submission-files')

urlpatterns = [
    re_path(r'^', include((api.urls, 'api'), namespace='api')),

    re_path(r"^get-token", authorization.api.views.RemoteAuthenticationView.as_view(), name="get-token"),
    re_path(r'^me', userprofile.api.views.MeDetail.as_view()),
    re_path(r'^lti-outcomes', external_services.api.views.LTIExerciseBasicOutcomesView.as_view(), name='lti-outcomes'),
    path('statistics/', lib.api.statistics.BaseStatisticsView.as_view(), name='statistics'),
    path(
        'courses/<int:course_id>/statistics/',
        course.api.views.CourseStatisticsView.as_view(),
        name='course-statistics'
    ),
    path(
        'exercises/<int:exercise_id>/statistics/',
        exercise.api.views.ExerciseStatisticsView.as_view(),
        name='exercise-statistics'
    ),
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
    # pylint: disable=unnecessary-lambda-assignment
    _get_methods = lambda v: ' '.join(((m[0].upper() if hasattr(v, m) else ' ') for m in _methods))
    _get_perms = lambda v: ', '.join(p.__class__.__name__ for p in v().get_permissions())
    _views = [(v.__name__, _get_methods(v), _get_perms(v)) for v in _views if not (v in _vseen or _vseen.add(v))]
    _lens['m'] = max(len(m) for v, m, p in _views)
    _perms = ("  - {:<{v:d}s} {:<{m:d}s} {:s}".format(*a, **_lens) for a in _views)
    print(" API PERMS:", *_perms, sep='\n')
    print(" API methods:", ', '.join(m.capitalize() for m in _methods))

    # clean vars out of memory
    del _urls, _lens, _vseen, _views, _methods, _get_methods, _get_perms, _perms
